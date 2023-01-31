import gurobipy as gp
from gurobipy import GRB
import random
import numpy as np
import plotly.express as px
import pandas as pd
from itertools import combinations, chain
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt
from auxiliary_functions import find_equipments


def schedule_meetings(comb,intervals, days,total_rooms_ids, capacities_room,equipments_room,  df_optimization,dct_rooms_caps, dct_rooms_eq_plot,  teams, meetings ,capacities_m,meeting_eq,defac_meeting_eq,  buffer_between_meetings=0, plot=True): 
    buffer_between_meetings=0

    # Create a new model
    model = gp.Model("Scheduling: New Formulation")
    model.Params.LogToConsole = 0

    # Decision Variables
    P = {}
    R = {}
    rooms= total_rooms_ids
    meeting_ids= meetings

    for d in days:
        for i in range(intervals):
            for j in rooms:
                for k in meeting_ids:
                        P[d, i, j, k] = model.addVar(vtype=GRB.BINARY, name=f'Plan_{d}_{i}_{j}_{k}') # judith

    for j in rooms:
        R[j] = model.addVar(vtype=GRB.BINARY, name=f'Room_{j}') # 1 if room is used, 0 otherwise
    
        
    model.setObjective(gp.quicksum(R[j[1]] * capacities_room[j[0]] for j in enumerate(rooms)), GRB.MINIMIZE)
    # Constraints
    for d in days:
        for i in range(intervals):
            for j in enumerate(rooms):
                    model.addConstr(gp.quicksum(P[d, i, j[1], k] for k in meeting_ids) <= 1,
                                        name='In each room, for any meeting of day, not more than one meeting can be happening')

                    model.addConstr(np.array([P[d, i, j[1], k] for k in meeting_ids]) @ np.array(capacities_m) <= capacities_room[j[0]],
                                        name='Capacity constraint')
                    #indicator constraint, only if the room is used, then check whether the equipemnts of room and reservation match 
                    for k in meeting_ids:
                            model.addConstr((P[d,i,j[1], k]==1 )>> (np.array([P[d,i,j[1], k] for k in meeting_ids]) @ np.array(meeting_eq) == equipments_room[j[0]]),
                                        name='Equipment constraint') 
           
    for d in days:
        for k in meeting_ids:
                model.addConstr(gp.quicksum(P[d, i, j, k] for i in range(intervals) for j in rooms) == 1,
                                    name='All reservations need to be planned')

    for d in days:
        for j in rooms:
                    model.addConstr(gp.quicksum(P[d, i, j, k] for i in range(intervals) for k in meeting_ids) <= 10000000 * R[j],
                                        name='If there is at least one meeting in the room, the room is occupied')

            
    for d in days:

        finish_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)][
                                                   'Finish time'].item() for k in meeting_ids]

        start_time_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item() - buffer_between_meetings
                            for k in meeting_ids]

        for i in range(1, intervals):
            for j in rooms:

                    previous_finish_time = np.array([P[d, i - 1, j, k] for k in meeting_ids]) @ np.array(finish_time_day)
                    next_start_time = np.array([P[d, i, j, k] for k in meeting_ids]) @ np.array(start_time_day)

                    model.addConstr(next_start_time >= previous_finish_time,
                                                    name='Simultaneous meetings are not allowed')

    model.write('Schedule.lp')
    #model.Params.timeLimit = 2*60
    model.optimize()

    if plot:

            data = []
            dictionary = {}
            for d in days:

                finish_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Finish time'].item() for k in meeting_ids]

                start_day = [df_optimization[(df_optimization['Day'] == d) & (df_optimization['ResCode'] == k)]['Start time'].item()
                                              + buffer_between_meetings for k in meeting_ids]

                dct_room_res= dict.fromkeys(rooms, [])
                try: 
                    if model.status == GRB.OPTIMAL:
                        for i in range(intervals):
                            for j in rooms:
                                if max([P[d, i, j, k].X for k in meeting_ids]) == 1: 
                                    # Pre - process data for the graph
                                    meeting_id = [P[d, i, j, k].X for k in meeting_ids].index(max([P[d, i, j, k].X for k in meeting_ids]))


                                    minutes_start = int(start_day[meeting_id] % 60)
                                    if minutes_start == 0:
                                        minutes_start = '00'
                                        minutes_finish = int(finish_day[meeting_id] % 60)
                                    if minutes_finish == 0:
                                        minutes_finish = '00'
                                    meeting_ids=list(meeting_ids)

                                                

                                    #index of reservation that belongs to room j 
                                    index = np.where(df_optimization['ResCode']==meeting_ids[meeting_id])[0][0]
                                    # add reservatios to dict if it is assigned to room j
                                    reservation = df_optimization.iloc[index]['Reservation']
                                    if dct_room_res[j]!=[]:
                                        dct_room_res[j].append(reservation)
                                    else:
                                        dct_room_res[j]= [reservation]
                                                
                                    dictionary['Room ID & Capacity'] = f'Room: {j}. Cap: {dct_rooms_caps[j]}. Equ: {dct_rooms_eq_plot[j]}'
                                    dictionary['Start'] = f'{d} {int(start_day[meeting_id] // 60)}:{minutes_start}:00'
                                    dictionary['End'] = f'{d} {int(finish_day[meeting_id] // 60)}:{minutes_finish}:00'
                                    dictionary['Reserver ID & Equipment'] = f'ID = {meeting_ids[meeting_id]} & Equ: {defac_meeting_eq[meeting_id]}'                                   
                                    dictionary['Meeting Capacity'] = capacities_m[meeting_id]
                                    data.append(dictionary)
                                    dictionary = {}

                                elif R[j].X == 0:

                                    #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {df_optimization[df_optimization["ResUnitCode"]==j]["ResUnitCapacity"].unique()[0]}'
                                    dictionary['Room ID & Capacity'] = f'Room: {j}. Cap: {dct_rooms_caps[j]}. Equ: {dct_rooms_eq_plot[j]}'
                                    data.append(dictionary)
                                    dictionary = {}
                                    
                        #create dictionary for each team on which floor they have a meeting
                        dct_team_floors = dict.fromkeys(teams, 0)
                        for team in teams: 
                            dct_team_floors[team]=team.floors_reservations(dct_room_res) # p_most_meetings
                                     
                        #print(dct_team_floors)
                                    

                        df = pd.DataFrame(data)
                                    
                        # final schedule
                        fig = px.timeline(df,
                                            x_start="Start",
                                            x_end="End",
                                            y='Room ID & Capacity',
                                            color='Meeting Capacity',
                                            text='Reserver ID & Equipment',
                                            title=f'Meeting schedule, day: {days[0]}, Floors: {comb}',
                                            # color_continuous_scale='portland'
                                            )

                        fig.update_traces(textposition='inside')
                        fig.update_layout(font=dict(size=17))
                        fig.write_html('Optmized Meeting schedule.html', auto_open=True)
                        return df, dct_team_floors
                except:

                    print("Model infeasible for combination of floors: ", comb)


