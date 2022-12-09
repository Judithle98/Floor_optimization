import gurobipy as gp
from gurobipy import GRB
import random
import numpy as np
import plotly.express as px
import pandas as pd
import datetime
from itertools import combinations, chain
import itertools
from matplotlib.ticker import MaxNLocator
from tqdm import tqdm
import matplotlib.pyplot as plt
#from auxiliary_functions import create_floor_col, dct_rooms_floor,create_perm,concat_perm_rooms, find_capacities,find_equipments, factorize_equipment
from auxiliary_functions import *
from schedule import schedule_rooms2
from schedule_equipment import schedule_rooms
from faker import Faker
from Person import Person
from statistics import mode
# load data meeting reservations
data = pd.read_csv('Data/Data_Planon_Nijmegen.csv', sep=';')

# load data meeting reservations
data_desks = pd.read_csv('Data/Data_Flexdesks.csv', sep=';')

# create seperate columns for date, start time, end time
data['ResStartDate'] = data['ResStartDateTime'].str.split(' ').str[0]
data['ResStartTime'] = data['ResStartDateTime'].str.split(' ').str[1]
data['ResEndDate'] = data['ResEndDateTime'].str.split(' ').str[0]
data['ResEndTime'] = data['ResEndDateTime'].str.split(' ').str[1]

# Choose a subset of data
data = data.dropna(subset=['ResUnitSpaceCategory'])
data = data[(data['ResUnitSpaceCategory'] != 'Archived') & (data['ResUnitCapacity'] > 0)]
data = data[data['ResUnitCode'] != 'NIJ REST']

data_optimization = data
data_optimization['Start time'] = data['ResStartTime'].str.split(':').str[0].astype(int)*60 + data['ResStartTime'].str.split(':').str[1].astype(int)
data_optimization['Finish time'] = data['ResEndTime'].str.split(':').str[0].astype(int)*60 + data['ResEndTime'].str.split(':').str[1].astype(int)
data_optimization['Capacities meeting'] = data_optimization['ResUnitCapacity']
data_optimization['Day'] = pd.to_datetime(data_optimization['ResStartDate'])

#Use auxiliary functions to preprocess data

#create column with all floors
data_optimization['Floor'] = create_floor_col(data_optimization)

data_desks['Floor'] = create_floor_col(data_desks, desks=True)

#obtian dict with room_floor and list of unique floors
dct, unique_floors= dct_floors_spaces(data_optimization)
dct_desks = dct_floors_spaces(data_desks, desks= True)

#obtain all permutations of floors
floors_perm= create_perm(unique_floors)
#dict for each permutation list of all rooms
d_rooms_caps = concat_perm_rooms(dct, floors_perm)


#Some data for the optimization model
intervals = 20
printing = True
incl_equipments= True
fake=Faker()
#make 2 new columns start and end
data_optimization['Start'] = pd.to_datetime(data_optimization.ResStartDateTime)
data_optimization['End'] = pd.to_datetime(data_optimization.ResEndDateTime)

data_optimization = data_optimization[data_optimization['ResStartDate'] == data_optimization['ResEndDate']]
data_optimization = data_optimization[(data_optimization['Finish time'] - data_optimization['Start time']) > 1]
data_optimization = data_optimization.sort_values(by='Start', ascending=True)

#days for which the allocations will run 
all_days = sorted(data_optimization['Start'].dt.strftime('%Y-%m-%d').unique())[5:7] # last argument changes the number of days


nr_people= 20
#departments = ["sales","development", "marketing", 'IT', "support", "HR"]
departments = ["sales","development", "marketing"]

team_names = np.array([fake.user_name() for i in range(10)])

teams = create_teams(departments,team_names)
employees= create_employees(nr_people,departments,teams, fake)
#create random team names


# for e in employees:
#         print(e.disp())


if incl_equipments:
    data_optimization['new_Equipment'] = data_optimization['ResUnitName']

    equipments= np.unique(data_optimization['new_Equipment'])
    equipments_clean = [eq for eq in equipments if  eq!='(Beamer)' and  eq!='(Smartboard)' and eq!='(Tv screen)' ]

    for eq in equipments_clean:
        data_optimization['new_Equipment']= data_optimization['new_Equipment'].replace(eq, '')

    labels,uniques , data_optimization = factorize_equipment(data_optimization)


for comb, rooms  in d_rooms_caps.items():
    print(comb)
    if comb ==('0','1','2','3','4'): 
        dct_rooms_caps = find_capacities(rooms, data_optimization)
        
        #for  equipemnts delete later
        dct_rooms_eq = find_equipments(rooms,data_optimization)


        capacities_room = list(dct_rooms_caps.values()) # pick all capacities for reserved rooms for specific day [[3.0, 2.0, 3.0, 6.0, 8.0, 6.0]]
        total_rooms_ids = list(dct_rooms_caps.keys())
        equipments_room = list(dct_rooms_eq.values())


        # if incl_equipments:
        #     #for equipments
        #     df =schedule_rooms(comb,intervals, all_days,total_rooms_ids, capacities_room, equipments_room,  data_optimization,dct_rooms_caps,dct_rooms_eq,employees,teams)      
        # else:
        #     #no equipments
        #     df =schedule_rooms(comb,intervals, all_days,total_rooms_ids, capacities_room,  data_optimization,dct_rooms_caps,employees)      


        for day in enumerate(tqdm(all_days)):
            if day[0] == len(all_days)-1: # just to stop at the end

                break
            else:

                buffer_between_meetings=0
                plot=True
                rescheduling=False

                df_optimization = data_optimization[(data_optimization.Start >= f'{day[1]} 00:00:00') & (data_optimization.Start <= f'{all_days[day[0]+1]} 00:00:00')]
                df_optimization['Room ID'] = ['ID: ' + str(x) for x in df_optimization["ResUnitCode"]]
                df_optimization['Room Cap'] = ['. Capacity: ' + str(x) for x in df_optimization["ResUnitCapacity"]]
                df_optimization['Room ID & Capacity'] = df_optimization['Room ID'] + df_optimization['Room Cap']
                
                #crete reservations
                #reservation = R
                #df_optimization['Reservation']= reservation
                
                capacities_m = df_optimization['Capacities meeting'].tolist() #= df_optimization['ResUnitCapacity']
                meeting_eq= list(df_optimization["new_Equipment"])

                meetings= df_optimization['ResCode']
                days_optimization = df_optimization['Start'].apply(lambda x: x.strftime('%Y-%m-%d')).unique()
                df_optimization, reservations = create_reservation_col(df_optimization, employees)
                add_p_reservations(reservations, employees)
                
                dict_team, p_most_meet_team, dict_team_members = p_most_meetings_per_team(teams,employees,reservations)
                
                #name of the member with the 
                print(dict_team)
                print(dict_team_members)
               
            
                #create list of floors for person
        
                # from all reservations we check which room is assigned to which floor
                # for the person with most reservations per team we check to which floor his reservations belong
                

                # Create a new model
                model = gp.Model("Scheduling: New Formulation")
                model.Params.LogToConsole = 0

                # Decision Variables
                P = {}
                R = {}
                days= days_optimization
                rooms= total_rooms_ids
                ids= meetings

                for d in days:
                    # ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
                    for i in range(intervals):
                        for j in rooms:
                            for k in ids:
                                    P[d, i, j, k] = model.addVar(vtype=GRB.BINARY, name=f'Plan_{d}_{i}_{j}_{k}') # judith

                for j in rooms:
                    R[j] = model.addVar(vtype=GRB.BINARY, name=f'Room_{j}') # 1 if room is used, 0 otherwise

                
                
                model.setObjective(gp.quicksum(R[j[1]] * capacities_room[j[0]] for j in enumerate(rooms)), GRB.MINIMIZE)
                # model.setObjective(gp.quicksum(U[f] for f in floors), GRB.MINIMIZE)
                # Constraints
                for d in days:
                    #ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
                    #capacities_m = data_optimization[data_optimization['Day'] == d]['Capacities meeting'].tolist()
                    for i in range(intervals):
                        for j in enumerate(rooms):
                                model.addConstr(gp.quicksum(P[d, i, j[1], k] for k in ids) <= 1,
                                                    name='In each room, for any meeting of day, not more than one meeting can be happening')

                                model.addConstr(np.array([P[d, i, j[1], k] for k in ids]) @ np.array(capacities_m) <= capacities_room[j[0]],
                                                    name='Capacity constraint')
                                #indicator constraint, only if the room is used, then check whether the equipemnts of room and reservation match 
                                for k in ids:
                                    model.addConstr((P[d,i,j[1], k]==1 )>> (np.array([P[d,i,j[1], k] for k in ids]) @ np.array(meeting_eq) == equipments_room[j[0]]),
                                        name='Equipment constraint') 
           
                for d in days:
                    # ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
                    for k in ids:
                            model.addConstr(gp.quicksum(P[d, i, j, k] for i in range(intervals) for j in rooms) == 1,
                                                name='All reservations need to be planned')

                for d in days:
                    # ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
                    for j in rooms:
                                model.addConstr(gp.quicksum(P[d, i, j, k] for i in range(intervals) for k in ids) <= 10000000 * R[j],
                                                name='If there is at least one meeting in the room, the room is occupied')

            
                for d in days:

                    #ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()

                    if rescheduling:
                        finish_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Finish time'].item()
                                               + change_meeting[d, k]*60 for k in ids]
                        start_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item()
                                              + change_meeting[d, k]*60 - buffer_between_meetings for k in ids]
                    else:
                        finish_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)][
                                                   'Finish time'].item() for k in ids]

                        start_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item() - buffer_between_meetings
                            for k in ids]

                    for i in range(1, intervals):
                        for j in rooms:

                                previous_finish_time = np.array([P[d, i - 1, j, k] for k in ids]) @ np.array(finish_time_day)
                                next_start_time = np.array([P[d, i, j, k] for k in ids]) @ np.array(start_time_day)

                                model.addConstr(next_start_time >= previous_finish_time,
                                                    name='Simultaneous meetings are not allowed')

                model.write('Rescheduling.lp')
                #model.Params.timeLimit = 2*60
                model.optimize()


       
                #print(model.getVars())
                if plot:

                        data = []
                        dictionary = {}
                        for d in days:

                            #ids = idata_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
                            #capacities_meeting_day = data_optimization[data_optimization['Day'] == d]['Capacities meeting'].tolist()

                            if rescheduling:
                                finish_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Finish time'].item()
                                              + change_meeting[d, k].X * 60 for k in ids]

                                start_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item()
                                              + change_meeting[d, k].X * 60 + buffer_between_meetings for k in ids]
                            else:
                                finish_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Finish time'].item() for k in ids]

                                start_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item()
                                              + buffer_between_meetings for k in ids]

                            dct_room_res= dict.fromkeys(rooms, [])
                        
                            for i in range(intervals):
                                for j in rooms:
                                    if max([P[d, i, j, k].X for k in ids]) == 1: 
                                        # Pre - process data for the graph
                                        meeting_id = [P[d, i, j, k].X for k in ids].index(max([P[d, i, j, k].X for k in ids]))

                                        minutes_start = int(start_day[meeting_id] % 60)
                                        if minutes_start == 0:
                                            minutes_start = '00'
                                        minutes_finish = int(finish_day[meeting_id] % 60)
                                        if minutes_finish == 0:
                                            minutes_finish = '00'
                                        ids=list(ids) 

                                        #obtain all reservations assigned to room
                                        #for r in reservations: 

                                        #index of reservation that belongs to room j 
                                        index = np.where(df_optimization['ResCode']==ids[meeting_id])[0][0]
                                       
                                        # add reservatios to dict if it is assigned to room j
                                        reservation = df_optimization.iloc[index]['Reservation']
                                        if dct_room_res[j]!=[]:
                                            dct_room_res[j].append(reservation)
                                        else:
                                            dct_room_res[j]= [reservation]

                                      
                                        #dct_room_res[j]= reservation   # dict room assigned to reservation
                                        dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}. Equipment: {dct_rooms_eq[j]}'
                                        #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}'
                                        dictionary['Start'] = f'{d} {int(start_day[meeting_id] // 60)}:{minutes_start}:00'
                                        dictionary['End'] = f'{d} {int(finish_day[meeting_id] // 60)}:{minutes_finish}:00'
                                        dictionary['Meeting ID & Equipment & Person'] = f'ID = {ids[meeting_id]} & Equ: {meeting_eq[meeting_id]} Reserver: {reservation.reserver.disp_short()}'
                                        dictionary['Meeting Capacity'] = capacities_m[meeting_id]
                                        
                                     
                            
            
                                        data.append(dictionary)
                                        dictionary = {}

                                    elif R[j].X == 0:

                                        #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {df_optimization[df_optimization["ResUnitCode"]==j]["ResUnitCapacity"].unique()[0]}'

                                        dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}. Equipment: {dct_rooms_eq[j]}'
                                        data.append(dictionary)
                                        dictionary = {}
                            print(dct_room_res) 
                            dict_p_floors= dict.fromkeys(p_most_meet_team, 0)
                        #for the person with the most meetings, find all floors for all reservations he/she is involved in
                       
                       ## creates dict for most busy person & the floors of the meetings
                        for p in p_most_meet_team:
                            l = []
                            for res in p.reservations:
                                for k,v in dct_room_res.items():
                                    if res in v:
                                        l.append(findFloor(k))
                            dict_p_floors[p]= l
                                
                        print(dict_p_floors)
                        
                        ## creates dict per team all floors & t
                        teams = np.array(teams).flatten().tolist()
                        dct_team_floors = dict.fromkeys(teams,0)
                    
                        for team, members in dict_team_members.items():
                                l = []
                                for p in members: 
                                    for res in p.reservations: 
                                        for k,v in dct_room_res.items():
                                            if res in v:
                                                l.append(findFloor(k))
                                dct_team_floors[team]= l
                        print('-----------------------------------')
                        print(dct_team_floors)
                        print(dict_p_floors)






                    
                        for k,v in dict_p_floors.items():
                            print(k.disp_short())
                            print(len(k.reservations))
                            print(v)

                        #mode of dict_p_floors returns the floor where the most meetings of the person with the mot meetings of a team are held 
                        for k,v in dict_p_floors.items():
                            mode_floor= mode(v)
                            print(mode_floor)
                            #get size of team + check if there is flex desks there


                       # meetings_team= dict.fromkeys(list(teams))
                        

                        df = pd.DataFrame(data)
                        
                        # final schedule
                        fig = px.timeline(df,
                                              x_start="Start",
                                              x_end="End",
                                              y='Room ID & Capacity',
                                              color='Meeting Capacity',
                                              text='Meeting ID & Equipment & Person',
                                              title=f'Final schedule, day: {day[1]}, Floors: {comb}',
                                              # color_continuous_scale='portland'
                                              )

                        fig.update_traces(textposition='inside')
                        # fig.update_yaxes(categoryorder = 'category ascending')
                        fig.update_layout(font=dict(size=17))
                        fig.write_html('second_figure_rescheduling_final_week.html', auto_open=True)
        
 