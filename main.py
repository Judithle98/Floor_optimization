import gurobipy as gp
import numpy as np
import plotly.express as px
import pandas as pd
from itertools import combinations, chain
from matplotlib.ticker import MaxNLocator
from tqdm import tqdm
import matplotlib.pyplot as plt
#from auxiliary_functions import create_floor_col, dct_rooms_floor,create_perm,concat_perm_rooms, find_capacities,find_equipments, factorize_equipment
from auxiliary_functions import *
from schedule_equipment import schedule_rooms
from schedule_desks import schedule_desks
from faker import Faker
from collections import Counter

from statistics import mode
# load data meeting reservations
data = pd.read_csv('Data/Data_Planon_Nijmegen.csv', sep=';')

# load data flex desk reservations
data_desks = pd.read_csv('Data/Data_FlexDesks_Full.csv', sep=';')

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
#obtian dict with room_floor and list of unique floors#
dct, unique_floors= dct_floors_spaces(data_optimization)
dct_desks = dct_floors_spaces(data_desks, desks= True)[0]

#create zones
zones = create_zones(data_desks)

#obtain all permutations of floors
floors_perm= create_perm(unique_floors)

#dict for each permutation list of all rooms/desks
d_perm_rooms = concat_perm_rooms(dct, floors_perm)
d_perm_desks = concat_perm_rooms(dct_desks, floors_perm)
d_perm_zones = find_perm_zones(zones, floors_perm)

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
print(all_days)
nr_people= 20
#departments = ["sales","development", "marketing", 'IT', "support", "HR"]
departments = ["sales","development", "marketing"]


teams = create_teams(departments, 2)
employees= create_employees(nr_people,teams, fake)

if incl_equipments:
    data_optimization['new_Equipment'] = data_optimization['ResUnitName']
    equipments= np.unique(data_optimization['new_Equipment'])
    equipments_clean = [eq for eq in equipments if  eq!='(Beamer)' and  eq!='(Smartboard)' and eq!='(Tv screen)' ]

    for eq in equipments_clean:
        data_optimization['new_Equipment']= data_optimization['new_Equipment'].replace(eq, '')

    labels, uniques , data_optimization = factorize_equipment(data_optimization)
    
    ###FLEX DESK####
    #initialize Desk object column
    # data_desks['Desk']= 0
    # equipments_desks= ['silent', 'window', 'adjustable desk' ]
    # data_desks['Equipment']=random.choice(equipments_desks)
    # for i, row in data_desks.iterrows:
    #     data_desks.at[i, 'Desk']= Desk(data_desk[])


##Create fake teams and assign them to reservations in df_optimization for specific day
for day in enumerate(all_days):
    if day[0] == len(all_days)-1: # just to stop at the end

             break
    else:
        #obtain reservation list for specific day
        df_optimization = data_optimization[(data_optimization.Start >= f'{day[1]} 00:00:00') & (data_optimization.Start <= f'{all_days[day[0]+1]} 00:00:00')]
                    
        # crete reservations         
        capacities_m = df_optimization['Capacities meeting'].tolist() #list of all meeting capacities
        meeting_eq= list(df_optimization["new_Equipment"])# list of factorized meeting equipments

        meetings= df_optimization['ResCode'] #list of meeting ids
        days = df_optimization['Start'].apply(lambda x: x.strftime('%Y-%m-%d')).unique()

        #turn all reservations into a Reservation object + randmly adds employees to those reservations
        df_optimization, meeting_reservations = create_reservation_col(df_optimization, employees)
        desk_reservations= create_desks_reservations(employees)
        # add all reservations to specific employees
        #add_p_reservations(meeting_reservations, employees) # add reservations per person
        for e in employees:
            e.add_reservations(meeting_reservations)
            e.add_reservations(desk_reservations)
        

        #add all reservations per team
        for team in teams:
                team.add_reservations()

##run scheduling algorithm for all floor combinations
for comb, rooms  in d_perm_rooms.items():
        
        if comb == ('1', '2', '4'):
            #per floor combination we obtain dict of rooms-capacities and rooms-equipments
            dct_rooms_caps = find_capacities(rooms, data_optimization)
            dct_rooms_eq = find_equipments(rooms,data_optimization)


            capacities_room = list(dct_rooms_caps.values()) # pick all capacities for reserved rooms for specific day [[3.0, 2.0, 3.0, 6.0, 8.0, 6.0]]
            total_rooms_ids = list(dct_rooms_caps.keys())
            equipments_room = list(dct_rooms_eq.values())

            if incl_equipments:
                #for equipments
                df, dct_team_floors= schedule_rooms(comb,intervals,  days,total_rooms_ids, capacities_room,equipments_room,  df_optimization,dct_rooms_caps,dct_rooms_eq,  teams, meetings ,capacities_m,meeting_eq, buffer_between_meetings=0, plot=True)

            else:
                #no equipments
                df =schedule_rooms(comb, intervals, all_days,days, total_rooms_ids, capacities_room,  data_optimization,dct_rooms_caps,employees, meetings, capacities_m, meeting_eq)      


# #print(dct_team_floors)
# reservation_caps = [] #per team capacities of desks required
# reservation_equipments= []
# e= []
# for team in teams:
#     print(team.name)
#     equips = []
#     # floor where the team has most meetings
#     mode_floors = mode(dct_team_floors[team])
#     # obtain all desks from that floor
#     if mode_floors=='1':# no flex desks on floor 1
#         mode_floors='2'
#     desks= dct_desks[mode_floors]
#     flex_res= list(team.desks_reservations())
#     flex_desk_noSilent=[]
#     for res in flex_res:
#         #print(res.equipment)
#         if res.equipment !='silent':
#             #check where the person has most meetings which floor & choose silent room on that floor
#             flex_desk_noSilent.append(res)
#             equips.append(res.equipment)
#     reservation_caps.append(len(flex_desk_noSilent)) # capacity the number of flex desks reserved in a team
#     reservation_equipments.append(equips)

#     # floor where team has most meetings 
# print(reservation_caps) 
# print('---------------------')
# print(reservation_equipments)



# incl_zones=True
# if incl_zones: 

#     mode_floors=[]
#     for team  in teams:
#         mode_floors.append(mode(dct_team_floors[team]))

#     ######only to test delete later

#     print('-------------------------------')
#     ##run scheduling algorithm for all floor combinations
#     for comb, zones  in d_perm_zones.items(): 
           
                
#             if comb == ('1', '2', '4'):

                        
#                         #per floor combination find all available zones 
#                         dct_zones_caps = find_zone_capacities(zones)
                        
#                         capacities_zones = list(dct_zones_caps.values()) # pick all capacities for reserved rooms for specific day [[3.0, 2.0, 3.0, 6.0, 8.0, 6.0]]
#                         floors_zones= [z.floor for z in zones]
#                         equipments_zones= [z.equipments for z in zones ]

#                         uniques= np.unique([item for sublist in equipments_zones for item in sublist])
#                         fact_numbers= np.random.randint(99999, size=len(uniques))
#                        # print(fact_numbers)
#                         for i,e in enumerate(equipments_zones):
#                                 for j, item in enumerate(e):
#                                     if item=='adjustable desk':
#                                         equipments_zones[i][j]=fact_numbers[0]
#                                     elif item=='window': 
#                                         equipments_zones[i][j]=fact_numbers[1]
#                         for i,e in enumerate(reservation_equipments):
#                                 for j, item in enumerate(e):
#                                     if item=='adjustable desk':
#                                         reservation_equipments[i][j]=fact_numbers[0]
#                                     elif item=='window': 
#                                         reservation_equipments[i][j]=fact_numbers[1]
                        
#                         #print(reservation_equipments)
#                         ## turn reservatio equipments into counts for each element
                       

                    #################aSSIGN TEAMS TO ZONES ACCORDING TO THE EQUIPMENTS#############
                    




















                        # all_counts=[]
                        # for res in reservation_equipments:
                        #     reservation_counts =np.zeros(len(uniques))
                        #     for e in res:
                        #         if e==fact_numbers[0]:
                        #             reservation_counts[0] = reservation_counts[0]+1
                        #         elif e== fact_numbers[1]:
                        #             reservation_counts[1] = reservation_counts[1]+1
                        #     all_counts.append(reservation_counts.tolist())
                        # all_counts_zones=[]
                        # for z in equipments_zones:
                        #     reservation_counts =np.zeros(len(uniques))
                        #     for e in z:
                        #         if e==fact_numbers[0]:
                        #             reservation_counts[0] = reservation_counts[0]+1
                        #         elif e== fact_numbers[1]:
                        #             reservation_counts[1] = reservation_counts[1]+1
                        #     all_counts_zones.append(reservation_counts.tolist())
                        # reservation_counts =np.zeros(len(uniques))
                        # uniques, counts= np.unique(z, return_counts=True)
                        # zone_counts.append(counts)
                        #print(reservation_equipments)
                        #print(all_counts)
                        #     uniques, counts= np.unique(  res , return_counts=True)
                        #     reservation_counts.append(counts)
                        # zone_counts= = np.zeros(len(equipments))
                        # for z in equipments_zones:
                        #     uniques, counts= np.unique(z, return_counts=True)
                        #     zone_counts.append(counts)
                        #all_counts=[[0,0] ,[0,0],[0,0]]
#####################
                        # to test 

#                        index_first = [ i  for i,z in enumerate(zones) if z.name=='DR'][0]
                        # index_second= [ i  for i,z in enumerate(zones) if z.name=='L'][0]
                        # index_third = [ i  for i,z in enumerate(zones) if z.name=='G'][0]

                        # print(zones[index_first])
                        # print(capacities_zones[index_first])
                        # print(equipments_zones[index_first])
                        # print('-----------')

                        # print(zones[index_second])
                        # print(capacities_zones[index_second])
                        # print(equipments_zones[index_second])
                        # print('-----------')
                        # print(zones[index_third])
                        # print(capacities_zones[index_third])
                        # print(equipments_zones[index_third])
                        # print('-----------')

                        # print(reservation_caps)
                        # print(reservation_equipments)
                        
                        # ## problem might arise if
                        # model = gp.Model("Allocation employees to flex desks")
                        # model.Params.LogToConsole = 0

                        # # Decision Variables
                        # P = {}
                        # D = {} #
                        # #zones= total_zone_ids
                        # meeting_ids= teams


                        # ## fact. equipments:
                        

            
                        # for j in zones:
                        #     for k in meeting_ids:
                        #             P[j, k] = model.addVar(vtype=GRB.BINARY, name=f'Plan_{j}_{k}') # judith

                        # for j in zones:
                        #     D[j] = model.addVar(vtype=GRB.BINARY, name=f'Zone_{j.name}') # 1 if room is used, 0 otherwise
                        
                            
                        # model.setObjective(gp.quicksum(D[j[1]] * capacities_zones[j[0]] for j in enumerate(zones)), GRB.MINIMIZE)
                        # # Constraints
                    
                        # for index,j in enumerate(zones):
                        #                 model.addConstr(gp.quicksum(P[j, k] for k in meeting_ids) <= 1,
                        #                                     name='Only one team can be allcoated to each zone')

                        #                 model.addConstr(np.array([P[j, k] for k in meeting_ids]) @ np.array(reservation_caps) <= capacities_zones[index],
                        #                                     name='Capacity constraint')
                                        
                        #                 for k in meeting_ids: 
                        #                             model.addConstrs((P[j, k]==1 ) >> (np.array([P[j, k] for k in meeting_ids]) @ np.array(mode_floors) == int(floors_zones[index])),
                        #                                             name='Team should sit where it has the most meetings')

                                               
                        #                            ##best version so far
                        #                             # model.addConstr( (P[j[1], k]==1 ) >> gp.quicksum([int(booli) for booli in [all_counts[i]<= all_counts_zones[i] for i,x in enumerate(uniques) ]])==2,
                                                
                        #                             #                  name='All requirements need to be available in a zone') 
                                                    
                        #                             #model.addConstr((P[j[1], k]==1 ) >> gp.quicksum([ int(counts[j]<= x[j]) for y, counts in enumerate(all_counts) for i,x in enumerate(all_counts_zones) for j in range(2)])==2, name='All requirements need to be available in a zone') 
                        #                 #current try
                        #                 #for i, k in enumerate(meeting_ids):
             
                        #                         # print(reservation_equipments[i])
                        #                         # print(equipments_zones[index])
                        #                         # print(int(not Counter(reservation_equipments[i])- Counter(equipments_zones[index]))==1)
                                                
                        
                        #                         # print(type(int( not Counter(reservation_equipments[i])- Counter(equipments_zones[index])))==1)))
                        #                         #print(int(all(item in equipments_zones[index] for item in reservation_equipments[i])))
                                                
                                              
                                               
                        #                         #model.addConstr((P[j, k]==1 ) >> int(all(item in equipments_zones[index] for item in reservation_equipments[i]))==1, name='All requirements need to be available in a zone') 
                        #                       #  model.addConstr( (P[j, k]==1 ) >> (int(not Counter(reservation_equipments[i])- Counter(equipments_zones[index]))==1), name='All requirements need to be available in a zone') 

                              
                        # for k in meeting_ids:
                        #             model.addConstr(gp.quicksum(P[j, k]  for j in zones) == 1,
                        #                                 name='All teams need to be allocated')


                        # for j in zones:
                        #             model.addConstr(gp.quicksum(P[j, k] for k in meeting_ids) <= 10000000 * D[j],
                        #                                         name='If there is at least one team assigned to zone, the zone is occupied')

                                
                        # model.write('Allocation_Teams_Zones.lp')
                        # #model.Params.timeLimit = 2*60
                        # model.optimize()

                        # print(model.getVars())
                        # plot=True
                        # if plot:

                        #         data = []
                        #         dictionary = {}
                                
                            
                        #         dct_zone_res= dict.fromkeys(zones, [])
                        #         # try:
                                
                        #         if model.status == GRB.OPTIMAL:
                        #                         for j in zones:
                        #                             if max([P[ j, k].X for k in meeting_ids]) == 1: 
                        #                                 # Pre - process data for the graph
                        #                                 meeting_id = [P[ j, k].X for k in meeting_ids].index(max([P[ j, k].X for k in meeting_ids]))

                                                
                        #                                 #index of reservation that belongs to room j 
                        #                                 #index = np.where(df_optimization['ResCode']==meeting_ids[meeting_id])[0][0]
                        #                                 team = meeting_ids[meeting_id] # team that is assigned to zone j
                                                        
                                                                    
                        #                                 #dictionary['Zone & Capacity'] = f'Zone {j}. Capacity: {dct_zones_caps[j]}. Equipment: {dct_rooms_eq[j]}'
                        #                                 dictionary['Zone & Capacity'] = f'Zone {j.name}, Capacity: {dct_zones_caps[j]}, Floor: {j.floor}'

                        #                                 #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}'
                        #                                 dictionary['Start'] = f'08:00'
                        #                                 dictionary['End'] = f'10:00'
                        #                                 dictionary['Team'] = f'ID = {team.name}'
                        #                                 dictionary['Size Team'] =   len(team.members)  #reservation_caps[meeting_id]
                        #                                 data.append(dictionary)
                        #                                 dictionary = {}

                        #                             elif D[j].X == 0:

                        #                                 #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {df_optimization[df_optimization["ResUnitCode"]==j]["ResUnitCapacity"].unique()[0]}'

                        #                                 dictionary['Zone & Capacity'] = f'Zone {j.name}, Capacity: {dct_zones_caps[j]}, Floor: {j.floor}'
                        #                                 data.append(dictionary)
                        #                                 dictionary = {}
                
                        #                         df = pd.DataFrame(data)
                        #                         # final schedule
                        #                         fig = px.timeline(df,
                        #                                                 x_start='Start',
                        #                                                 x_end='End',
                        #                                                 y=' Zone & Capacity',
                        #                                                 color='Size Team',
                        #                                                 text='Team',
                        #                                                 title=f'Final allocation, Floors: {comb}',
                        #                                                 # color_continuous_scale='portland'
                        #                                                 )
                        #                         fig.update_traces(textposition='inside')
                        #                         # fig.update_yaxes(categoryorder = 'category ascending')
                        #                         fig.update_layout(font=dict(size=17))
                        #                         fig.write_html('Schedule_final_week.html', auto_open=True)

                        #         else: 

                        #             raise Exception("No optimal solution found")
                                

                            