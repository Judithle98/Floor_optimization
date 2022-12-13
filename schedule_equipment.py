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
from auxiliary_functions import create_reservation_col, p_most_meetings_per_team, add_p_reservations


def schedule_rooms(comb,intervals, all_days,total_rooms_ids, capacities_room,equipments_room,  data_optimization,dct_rooms_caps,dct_rooms_eq, employees, teams, buffer_between_meetings=0, plot=True): 

    #try: 
        
        for day in enumerate(tqdm(all_days)):
            if day[0] == len(all_days)-1: # just to stop at the end

                break
            else:

                buffer_between_meetings=0

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
                if comb==('0'):
                    df_optimization, reservations = create_reservation_col(df_optimization, employees)
                    add_p_reservations(reservations, employees) # add reservations per person
                    #add all reservations per team
                    for team in teams:
                        team.add_reservations()

                #dict_team_most_meetings,  dict_team_members = p_most_meetings_per_team(teams,employees,reservations)
                #type(reservations)
                #dict_team, p_most_meet_team = p_most_meetings_per_team(teams,employees,reservations)
                #name of the member with the 
                #print(dict_team)
                #print(p_most_meet_team)

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
                    for k in ids:
                            model.addConstr(gp.quicksum(P[d, i, j, k] for i in range(intervals) for j in rooms) == 1,
                                                name='All reservations need to be planned')

                for d in days:
                    # ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
                    for j in rooms:
                                model.addConstr(gp.quicksum(P[d, i, j, k] for i in range(intervals) for k in ids) <= 10000000 * R[j],
                                                name='If there is at least one meeting in the room, the room is occupied')

            
                for d in days:

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

                model.write('Schedule.lp')
                #model.Params.timeLimit = 2*60
                model.optimize()

                #print(model.getVars())
                if plot:

                        data = []
                        dictionary = {}
                        for d in days:

                            finish_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Finish time'].item() for k in ids]

                            start_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item()
                                              + buffer_between_meetings for k in ids]

                            dct_room_res= dict.fromkeys(rooms, [])
                            try: 
                                if model.status == GRB.OPTIMAL:
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

                                                
                                            
                                            
                                                #index of reservation that belongs to room j 
                                                index = np.where(df_optimization['ResCode']==ids[meeting_id])[0][0]
                                                # add reservatios to dict if it is assigned to room j
                                                reservation = df_optimization.iloc[index]['Reservation']
                                                if dct_room_res[j]!=[]:
                                                    dct_room_res[j].append(reservation)
                                                else:
                                                    dct_room_res[j]= [reservation]
                                                
                                                
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
                                    
                                    #create dictionary for each team on which floor they have a meeting
                                    dct_team_floors = dict.fromkeys(teams, [])
                                    for team in teams: 
                                        dct_team_floors[team]=team.floors_reservations(dct_room_res)
                                    
                                    print(dct_team_floors)
                                    

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
                                    fig.write_html('Schedule_final_week.html', auto_open=True)
                                    return df
                            except:

                                print("Model infeasible for combination of floors: ", comb)


