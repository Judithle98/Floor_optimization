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


def schedule_rooms(comb,intervals, all_days,total_rooms_ids, capacities_room,equipments_room,  data_optimization,dct_rooms_caps,dct_rooms_eq, buffer_between_meetings=0,   max_shifted_hours=1, percent_meetings_allowed_for_rescheduling = 0.1, penatly_coefficient=1, rescheduling=False, plot=True): 

    try: 
        
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
            
                capacities_m = df_optimization['Capacities meeting'].tolist() #= df_optimization['ResUnitCapacity']
                meeting_eq= list(df_optimization["new_Equipment"])

                meetings= df_optimization['ResCode']
                days_optimization = df_optimization['Start'].apply(lambda x: x.strftime('%Y-%m-%d')).unique()
                #print(df_optimization)



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

                
                if rescheduling:
                    change_meeting = {}
                    change_meeting_abs = {}
                    change_meeting_ceil = {}

                    for d in days:
                        # ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
                        for k in ids:
                            change_meeting[d, k] = model.addVar(vtype=GRB.SEMIINT, lb=-max_shifted_hours, ub=max_shifted_hours, name=f'Changing meeting_{d}_{k}')
                            change_meeting_abs[d, k] = model.addVar(vtype=GRB.INTEGER, name=f'Changing meeting_Absolute_{d}_{k}')
                            change_meeting_ceil[d, k] = model.addVar(vtype=GRB.INTEGER, name=f'Changing meeting_Rounded_{d}_{k}')

        
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

                if rescheduling:
                    for d in days:
                        #ids = data_optimization[data_optimization['Day'] == d]['ResCode'].tolist()
                        for k in ids:
                            model.addConstr(change_meeting_abs[d, k] == gp.abs_(change_meeting[d, k]),
                                                name='Setting an absolute value for the rescheduling')
                            model.addConstr(change_meeting_ceil[d, k] >= change_meeting_abs[d, k]/max_shifted_hours)
                            model.addConstr(change_meeting_ceil[d, k] <= change_meeting_abs[d, k]/max_shifted_hours + 0.999)

                            # At least some amount of meetings should change its time:
                            # print(f'PERCENT RESCHEDULING: {len([change_meeting_abs[d, k] for k in ids])*percent_meetings_allowed_for_rescheduling}')
                            # print(len([change_meeting_abs[d, k] for k in ids]))
                            model.addConstr(gp.quicksum(change_meeting_ceil[d, k] for k in ids) <= len([change_meeting_abs[d, k] for k in ids])*percent_meetings_allowed_for_rescheduling, name='Restricting rescheduling')
                            # model.addConstr(gp.quicksum(change_meeting_abs[d, k] for k in ids) >= 0, name='Allowing rescheduling')

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
                print('after optimize') 
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

                                        dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}. Equipment: {dct_rooms_eq[j]}'
                                        #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}'
                                        dictionary['Start'] = f'{d} {int(start_day[meeting_id] // 60)}:{minutes_start}:00'
                                        dictionary['End'] = f'{d} {int(finish_day[meeting_id] // 60)}:{minutes_finish}:00'
                                        dictionary['Meeting ID & Equipment'] = f'ID = {ids[meeting_id]} & Equ: {meeting_eq[meeting_id]}'
                                        dictionary['Meeting Capacity'] = capacities_m[meeting_id]


                                        data.append(dictionary)
                                        dictionary = {}

                                    elif R[j].X == 0:

                                        #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {df_optimization[df_optimization["ResUnitCode"]==j]["ResUnitCapacity"].unique()[0]}'

                                        dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}. Equipment: {dct_rooms_eq[j]}'
                                        data.append(dictionary)
                                        dictionary = {}

                        df = pd.DataFrame(data)
                        
                        # final schedule
                        fig = px.timeline(df,
                                              x_start="Start",
                                              x_end="End",
                                              y='Room ID & Capacity',
                                              color='Meeting Capacity',
                                              text='Meeting ID & Equipment',
                                              title=f'Final schedule, day: {day[1]}, Floors: {comb}',
                                              # color_continuous_scale='portland'
                                              )

                        fig.update_traces(textposition='inside')
                        # fig.update_yaxes(categoryorder = 'category ascending')
                        fig.update_layout(font=dict(size=17))
                        fig.write_html('second_figure_rescheduling_final_week.html', auto_open=True)
                                   
#                         try:
#                             values = [np.array([[R[j].X for j in rooms]]) * np.array([capacities_room])][0][0].astype(int).tolist()
#                             empty_rooms_positions = [i for i, e in enumerate(values) if e == 0]
#                             empty_rooms_capacities = [capacities_room[j] for j in empty_rooms_positions]
#                             used_rooms = len([i for i in values if i > 0])
#                             empty_rooms = len([empty_rooms_capacities])
#                         except:
#                             used_rooms = None
#                             empty_rooms = None

        return df
    except:
        print("Model infeasible. Reservations cannot be allocated on only floors: ", comb)