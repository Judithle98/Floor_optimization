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
from auxiliary_functions import create_floor_col, dct_rooms_floor,create_perm,concat_perm_rooms, find_capacities
from schedule import schedule_rooms2
from schedule_equipment import schedule_rooms

# load data
data = pd.read_csv('Data/Data_Planon_Nijmegen.csv', sep=';')

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
#obtian dict with room_floor and list of unique floors
dct,unique_floors = dct_rooms_floor(data_optimization)
#obtain all permutations of floors
floors_perm= create_perm(unique_floors)
#dict for each permutation list of all rooms
d_rooms_caps = concat_perm_rooms(dct, floors_perm)


#Some data for the optimization model
intervals = 20
printing = True
incl_equipments= True
#make 2 new columns start and end
data_optimization['Start'] = pd.to_datetime(data_optimization.ResStartDateTime)
data_optimization['End'] = pd.to_datetime(data_optimization.ResEndDateTime)

data_optimization = data_optimization[data_optimization['ResStartDate'] == data_optimization['ResEndDate']]
data_optimization = data_optimization[(data_optimization['Finish time'] - data_optimization['Start time']) > 1]
data_optimization = data_optimization.sort_values(by='Start', ascending=True)

#days for which the allocations will run 
all_days = sorted(data_optimization['Start'].dt.strftime('%Y-%m-%d').unique())[5:7] # last argument changes the number of days


# for equipments then delete later
def find_equipments(rooms, data):
    dict_room_eq= dict.fromkeys(rooms)
    for room in rooms: 
        index= np.where(data["ResUnitCode"]==room)[0][0]
        dict_room_eq[room]=data.iloc[index]["new_Equipment"]
        # make all empty string that are names and not equipemnts
#         string = "(Development only)"
#         for i, name in enumerate(data_optimization['ResUnitName']):
#             if string in name or name[0]!= "(": 
#                 print(name[0])

#                 print(data_optimization['ResUnitName'].iloc[i])
#                 data_optimization['ResUnitName'].iloc[i] = "" # change all development things to 0 

    return dict_room_eq    

def factorize_equipment(df_optimization):
    #for i in range(df_optimization.shape[0]
# #     string = "(Development only)"
#     for i, name in enumerate(df_optimization['ResUnitName']):
#         #print(name)
#         if name!= "(Beamer)" and name!= "(Smartboard)" and name!='(TV screen)': 
#             #print(df_optimization['ResUnitName'].iloc[i])
#             df_optimization['ResUnitName'].iloc[i] = "" # change all development things to 0 

    labels, uniques = df_optimization['new_Equipment'].factorize()
    df_optimization['new_Equipment']= labels
    # replace all 0"s to 9"s simply bc otherwise linearizaton doesnt work
    df_optimization['new_Equipment'] = df_optimization['new_Equipment'].replace(0, 9)

    return labels, uniques, df_optimization

# #equipments = ['(Beamer)', "(TV screen)", '(Smartboard)', ""]
# #data_optimization['Equipment'] = random.choices(equipments, k = data_optimization.shape[0])
# data_optimization['new_Equipment'] = data_optimization['ResUnitName']
# for i, eq in enumerate(data_optimization['ResUnitName']):
#     if eq!='(Smartboard)' and eq!='(Beamer)' and eq!='(Tv screen)':
#          data_optimization.at[i,'new_Equipment'] = ""

if incl_equipments:
    data_optimization['new_Equipment'] = data_optimization['ResUnitName']

    equipments= np.unique(data_optimization['new_Equipment'])
    equipments_clean = [eq for eq in equipments if  eq!='(Beamer)' and  eq!='(Smartboard)' and eq!='(Tv screen)' ]


    for eq in equipments_clean:
        data_optimization['new_Equipment']= data_optimization['new_Equipment'].replace(eq, '')

    labels,uniques , data_optimization = factorize_equipment(data_optimization)
    print(uniques)

for comb, rooms  in d_rooms_caps.items():

    dct_rooms_caps = find_capacities(rooms, data_optimization)
    
    #for  equipemnts delete later
    dct_rooms_eq = find_equipments(rooms,data_optimization) 
    #print(dct_rooms_eq)
    #print(dct_rooms_eq)
    # # print("Floors used:")
    # # print(comb)
    # # print("Available rooms and capacities")

    print(rooms)
    capacities_room = list(dct_rooms_caps.values()) # pick all capacities for reserved rooms for specific day [[3.0, 2.0, 3.0, 6.0, 8.0, 6.0]]
    total_rooms_ids = list(dct_rooms_caps.keys())
    equipments_room = list(dct_rooms_eq.values())
    
    if incl_equipments:
        #for equipments
        df =schedule_rooms(comb,intervals, all_days,total_rooms_ids, capacities_room, equipments_room,  data_optimization,dct_rooms_caps,dct_rooms_eq)      
    else:
        #no equipments
        df =schedule_rooms(comb,intervals, all_days,total_rooms_ids, capacities_room,  data_optimization,dct_rooms_caps)      
# for day in enumerate(tqdm(all_days)):
#             if day[0] == len(all_days)-1: # just to stop at the end

#                 break
#             else:

#                 buffer_between_meetings=0
#                 plot=True
#                 rescheduling=False

#                 df_optimization = data_optimization[(data_optimization.Start >= f'{day[1]} 00:00:00') & (data_optimization.Start <= f'{all_days[day[0]+1]} 00:00:00')]
#                 df_optimization['Room ID'] = ['ID: ' + str(x) for x in df_optimization["ResUnitCode"]]
#                 df_optimization['Room Cap'] = ['. Capacity: ' + str(x) for x in df_optimization["ResUnitCapacity"]]
#                 df_optimization['Room ID & Capacity'] = df_optimization['Room ID'] + df_optimization['Room Cap']
                
#                 capacities_m = df_optimization['Capacities meeting'].tolist() #= df_optimization['ResUnitCapacity']
#                 meeting_eq= df_optimization['new_Equipment'].tolist()
#                # meeting_eq = [9 for i in range(len(capacities_m))]
#                 print(meeting_eq)
#                 meetings= df_optimization['ResCode']
#                 days_optimization = df_optimization['Start'].apply(lambda x: x.strftime('%Y-%m-%d')).unique()
#                 #print(df_optimization)


#                 # Create a new model
#                 model = gp.Model("Scheduling: New Formulation")
#                 model.Params.LogToConsole = 0

#                 # Decision Variables
#                 P = {}
#                 R = {}
#                 days= days_optimization
#                 rooms= total_rooms_ids
#                 ids= meetings

#                 for d in days:
#                     # ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
#                     for i in range(intervals):
#                         for j in rooms:
#                             for k in ids:
#                                     P[d, i, j, k] = model.addVar(vtype=GRB.BINARY, name=f'Plan_{d}_{i}_{j}_{k}') # judith

#                 for j in rooms:
#                     R[j] = model.addVar(vtype=GRB.BINARY, name=f'Room_{j}') # 1 if room is used, 0 otherwise

                
#                 if rescheduling:
#                     change_meeting = {}
#                     change_meeting_abs = {}
#                     change_meeting_ceil = {}

#                     for d in days:
#                         # ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
#                         for k in ids:
#                             change_meeting[d, k] = model.addVar(vtype=GRB.SEMIINT, lb=-max_shifted_hours, ub=max_shifted_hours, name=f'Changing meeting_{d}_{k}')
#                             change_meeting_abs[d, k] = model.addVar(vtype=GRB.INTEGER, name=f'Changing meeting_Absolute_{d}_{k}')
#                             change_meeting_ceil[d, k] = model.addVar(vtype=GRB.INTEGER, name=f'Changing meeting_Rounded_{d}_{k}')

               

#                 model.setObjective(gp.quicksum(R[j[1]] * capacities_room[j[0]] for j in enumerate(rooms)), GRB.MINIMIZE)
#                 # model.setObjective(gp.quicksum(U[f] for f in floors), GRB.MINIMIZE)

#                 # Constraints
#                 for d in days:

#                     for i in range(intervals):
#                         for j in enumerate(rooms):
#                                 model.addConstr(gp.quicksum(P[d, i, j[1], k] for k in ids) <= 1,
#                                                     name='In each room, for any meeting of day, not more than one meeting can be happening')

#                                 #model.addConstr(np.array([P[d, i, j[1], k] for k in ids]) @ np.array(capacities_m) <= capacities_room[j[0]],
#                                 #                    name='Capacity constraint')
#                                 model.addConstr(np.array([P[d, i, j[1], k] for k in ids]) @ np.array(capacities_m) <= capacities_room[j[0]],
#                                                     name='Capacity constraint')

#                                 #model.addConstr(np.array([P[d, i, j[1], k] for k in ids]) @ np.array(meeting_eq) <= equipments_room[j[0]],
#                                 #                    name='Equipment constraint')
#                                 for k in ids:

#                                     model.addConstr((P[d,i,j[1], k]==1 )>> (np.array([P[d,i,j[1], k] for k in ids]) @ np.array(meeting_eq) == equipments_room[j[0]]),
#                                         name='Equipment constraint') 
#                                # model.addConstr((R[j[1  ]] ==1 )>> (gp.quicksum(P[d,i,j[1], k] *  meeting_eq[i] for i,k in enumerate(ids)) <= equipments_room[j[0]]),
#                                 #        name='Equipment constraint') 
#                                 #model.addConstr( (x[times[time_index-1],zone] == 1) >> (some constraint) )
#                 for d in days:
#                     # ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
#                     for k in ids:
#                             model.addConstr(gp.quicksum(P[d, i, j, k] for i in range(intervals) for j in rooms) == 1,
#                                                 name='All reservations need to be planned')

#                 for d in days:
#                     # ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
#                     for j in rooms:
#                                 model.addConstr(gp.quicksum(P[d, i, j, k] for i in range(intervals) for k in ids) <= 10000000 * R[j],
#                                                 name='If there is at least one meeting in the room, the room is occupied')

#                 if rescheduling:
#                     for d in days:
#                         #ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
#                         for k in ids:
#                             model.addConstr(change_meeting_abs[d, k] == gp.abs_(change_meeting[d, k]),
#                                                 name='Setting an absolute value for the rescheduling')
#                             model.addConstr(change_meeting_ceil[d, k] >= change_meeting_abs[d, k]/max_shifted_hours)
#                             model.addConstr(change_meeting_ceil[d, k] <= change_meeting_abs[d, k]/max_shifted_hours + 0.999)

#                             # At least some amount of meetings should change its time:
#                             # print(f'PERCENT RESCHEDULING: {len([change_meeting_abs[d, k] for k in ids])*percent_meetings_allowed_for_rescheduling}')
#                             # print(len([change_meeting_abs[d, k] for k in ids]))
#                             model.addConstr(gp.quicksum(change_meeting_ceil[d, k] for k in ids) <= len([change_meeting_abs[d, k] for k in ids])*percent_meetings_allowed_for_rescheduling, name='Restricting rescheduling')
#                             # model.addConstr(gp.quicksum(change_meeting_abs[d, k] for k in ids) >= 0, name='Allowing rescheduling')

#                 for d in days:

#                     #ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()

#                     if rescheduling:
#                         finish_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Finish time'].item()
#                                                + change_meeting[d, k]*60 for k in ids]
#                         start_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item()
#                                               + change_meeting[d, k]*60 - buffer_between_meetings for k in ids]
#                     else:
#                         finish_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)][
#                                                    'Finish time'].item() for k in ids]

#                         start_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item() - buffer_between_meetings
#                             for k in ids]

#                     for i in range(1, intervals):
#                         for j in rooms:

#                                 previous_finish_time = np.array([P[d, i - 1, j, k] for k in ids]) @ np.array(finish_time_day)
#                                 next_start_time = np.array([P[d, i, j, k] for k in ids]) @ np.array(start_time_day)

#                                 model.addConstr(next_start_time >= previous_finish_time,
#                                                     name='Simultaneous meetings are not allowed')

#                 model.write('Rescheduling.lp')
#                 #model.Params.timeLimit = 2*60
#                 model.optimize()
#                 #print(model.getVars())

#                 if plot:

#                         data = []
#                         dictionary = {}
#                         for d in days:

#                             #ids = idata_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
#                             #capacities_meeting_day = data_optimization[data_optimization['Day'] == d]['Capacities meeting'].tolist()

#                             if rescheduling:
#                                 finish_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Finish time'].item()
#                                               + change_meeting[d, k].X * 60 for k in ids]

#                                 start_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item()
#                                               + change_meeting[d, k].X * 60 + buffer_between_meetings for k in ids]
#                             else:
#                                 finish_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Finish time'].item() for k in ids]

#                                 start_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item()
#                                               + buffer_between_meetings for k in ids]


#                             for i in range(intervals):
#                                 for j in rooms:
#                                     if max([P[d, i, j, k].X for k in ids]) == 1:

#                                         # Pre - process data for the graph
#                                         meeting_id = [P[d, i, j, k].X for k in ids].index(max([P[d, i, j, k].X for k in ids]))


#                                         minutes_start = int(start_day[meeting_id] % 60)
#                                         if minutes_start == 0:
#                                             minutes_start = '00'
#                                         minutes_finish = int(finish_day[meeting_id] % 60)
#                                         if minutes_finish == 0:
#                                             minutes_finish = '00'
#                                         ids=list(ids)
#                                         # Add data to the dataframe for the graph
#                                         dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}. Equipment: {dct_rooms_eq[j]}'
#                                         #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}'
#                                         dictionary['Start'] = f'{d} {int(start_day[meeting_id] // 60)}:{minutes_start}:00'
#                                         dictionary['End'] = f'{d} {int(finish_day[meeting_id] // 60)}:{minutes_finish}:00'
#                                         dictionary['Meeting ID & Equipment'] = f'ID = {ids[meeting_id]} & Equ: {meeting_eq[meeting_id]}'
#                                         dictionary['Meeting Capacity'] = capacities_m[meeting_id]


#                                         if rescheduling:
#                                             dictionary['Changed Time'] = [change_meeting[d, k] for k in ids][meeting_id].X if [change_meeting[d, k] for k in ids][meeting_id].X != 0 else 0

#                                         data.append(dictionary)
#                                         dictionary = {}

#                                     elif R[j].X == 0:

#                                         #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {df_optimization[df_optimization["ResUnitCode"]==j]["ResUnitCapacity"].unique()[0]}'

#                                         dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}'
#                                         data.append(dictionary)
#                                         dictionary = {}

#                         df = pd.DataFrame(data)
                        
#                         # final schedule
#                         fig = px.timeline(df,
#                                               x_start="Start",
#                                               x_end="End",
#                                               y='Room ID & Capacity',
#                                               color='Meeting Capacity',
#                                               text='Meeting ID & Equipment',
#                                               title=f'Final schedule, day: {day[1]}, Floors: {comb}',
#                                               # color_continuous_scale='portland'
#                                               )

#                         fig.update_traces(textposition='inside')
#                         # fig.update_yaxes(categoryorder = 'category ascending')
#                         fig.update_layout(font=dict(size=17))
#                         fig.write_html('second_figure_rescheduling_final_week.html', auto_open=True)