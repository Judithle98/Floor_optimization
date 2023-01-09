import gurobipy as gp
from gurobipy import GRB
import random
import numpy as np
import plotly.express as px
import pandas as pd
from itertools import combinations, chain
from matplotlib.ticker import MaxNLocator
import matplotlib.pyplot as plt


#def schedule_desks( total_zone_ids, capacities_zone,equipments_zone,  df_optimization,dct_rooms_caps,dct_rooms_eq,  teams, meetings ,capacities_m,meeting_eq, buffer_between_meetings=0, plot=True): 
def schedule_desks(mode_floors, floors_zones, comb,zones, capacities_zones,equipments_zones,  dct_zones_caps,dct_rooms_eq,  teams, reservation_caps, reservation_equipments, plot=True):


    # Create a new model
                model = gp.Model("Allocation employees to flex desks")
                model.Params.LogToConsole = 0

                # Decision Variables
                P = {}
                D = {} #
                #zones= total_zone_ids
                meeting_ids= teams


                ## fact. equipments:
                

    
                for j in zones:
                    for k in meeting_ids:
                            P[j, k] = model.addVar(vtype=GRB.BINARY, name=f'Plan_{j}_{k}') # judith

                for j in zones:
                    D[j] = model.addVar(vtype=GRB.BINARY, name=f'Zone_{j.name}') # 1 if room is used, 0 otherwise
                
                    
                model.setObjective(gp.quicksum(D[j[1]] * capacities_zones[j[0]] for j in enumerate(zones)), GRB.MINIMIZE)
                # Constraints
            
                for j in enumerate(zones):
                                model.addConstr(gp.quicksum(P[j[1], k] for k in meeting_ids) <= 1,
                                                    name='Only one team can be allcoated to each zone')

                                model.addConstr(np.array([P[j[1], k] for k in meeting_ids]) @ np.array(reservation_caps) <= capacities_zones[j[0]],
                                                    name='Capacity constraint')
                                
                                for k in meeting_ids: 
                                            model.addConstr((P[j[1], k]==1 ) >> (np.array([P[j[1], k] for k in meeting_ids]) @ np.array(mode_floors) == int(floors_zones[j[0]])),
                                                            name='Team should sit where it has the most meetings')
                                
                                for k in meeting_ids:
                                            model.addConstr((P[j[1], k]==1 ) >> (gp.quicksum(e  for e in reservation_equipments[j[0]]) == equipments_zones[j[0]]),
                                                            name='All requirements need to be available in a zone')
                                
                            #    # indicator constraint, only if the room is used, then check whether the equipemnts of room and reservation match 
                                # for k in meeting_ids:
                                #     for e in reservation_equipments:
                                        
                                #           model.addConstr((P[j[1], k]==1 ) >> (np.array([P[j[1], k] for k in meeting_ids]) @ np.array(meeting_eq) == equipments_zones[j[0]]),
                                #                     name='All team requirements need to be available in the zone') 
                                        # model.addConstr((P[j[1], k]==1 )>> (np.array([P[j[1], k] for k in meeting_ids]) @ np.array(meeting_eq) == equipments_room[j[0]]),
                                        #             name='All team requirements need to be available in the zone')
            
                for k in meeting_ids:
                            model.addConstr(gp.quicksum(P[j, k]  for j in zones) == 1,
                                                name='All teams need to be allocated')


                for j in zones:
                            model.addConstr(gp.quicksum(P[j, k] for k in meeting_ids) <= 10000000 * D[j],
                                                        name='If there is at least one team assigned to zone, the zone is occupied')

                        
                model.write('Allocation_Teams_Zones.lp')
                #model.Params.timeLimit = 2*60
                model.optimize()

                print(model.getVars())
                plot=True
                if plot:

                        data = []
                        dictionary = {}
                        
                    
                        dct_zone_res= dict.fromkeys(zones, [])
                        # try:
                        
                        if model.status == GRB.OPTIMAL:
                                        for j in zones:
                                            if max([P[ j, k].X for k in meeting_ids]) == 1: 
                                                # Pre - process data for the graph
                                                meeting_id = [P[ j, k].X for k in meeting_ids].index(max([P[ j, k].X for k in meeting_ids]))

                                           
                                                #index of reservation that belongs to room j 
                                                #index = np.where(df_optimization['ResCode']==meeting_ids[meeting_id])[0][0]
                                                team = meeting_ids[meeting_id] # team that is assigned to zone j
                                                
                                                            
                                                #dictionary['Zone & Capacity'] = f'Zone {j}. Capacity: {dct_zones_caps[j]}. Equipment: {dct_rooms_eq[j]}'
                                                dictionary['Zone & Capacity'] = f'Zone {j.name}, Capacity: {dct_zones_caps[j]}, Floor: {j.floor}'

                                                #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {dct_rooms_caps[j]}'
                                                dictionary['Start'] = f'08:00'
                                                dictionary['End'] = f'10:00'
                                                dictionary['Team'] = f'ID = {team.name}'
                                                dictionary['Size Team'] =   len(team.members)  #reservation_caps[meeting_id]
                                                data.append(dictionary)
                                                dictionary = {}

                                            elif D[j].X == 0:

                                                #dictionary['Room ID & Capacity'] = f'ID: {j}. Capacity: {df_optimization[df_optimization["ResUnitCode"]==j]["ResUnitCapacity"].unique()[0]}'

                                                dictionary['Zone & Capacity'] = f'Zone {j.name}, Capacity: {dct_zones_caps[j]}, Floor: {j.floor}'
                                                data.append(dictionary)
                                                dictionary = {}
          
                                        df = pd.DataFrame(data)
                                        # final schedule
                                        fig = px.timeline(df,
                                                                x_start='Start',
                                                                x_end='End',
                                                                y='Zone & Capacity',
                                                                color='Size Team',
                                                                text='Team',
                                                                title=f'Final allocation, Floors: {comb}',
                                                                # color_continuous_scale='portland'
                                                                )
                                        fig.update_traces(textposition='inside')
                                        # fig.update_yaxes(categoryorder = 'category ascending')
                                        fig.update_layout(font=dict(size=17))
                                        fig.write_html('Schedule_final_week.html', auto_open=True)

                                        return df
                        else: 

                            raise Exception("No optimal solution found")
                        


