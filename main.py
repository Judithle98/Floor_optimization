import numpy as np
import pandas as pd
from auxiliary_functions import *
from schedule_meetings import schedule_meetings
from schedule_workspaces import *
from preprocessing import preprocess_data, generate_teams_and_reservations

#################################DATA############################
# load data meeting reservations
data = pd.read_csv('Data/Data_Planon_Nijmegen.csv', sep=';')
# load data flex desk reservations
data_desks = pd.read_csv('Data/Data_FlexDesks_Full.csv', sep=';')

############################PREPROCESSING########################
data_optimization, dct, unique_floors,dct_desks, zones, silent_zones = preprocess_data(data, data_desks)

#obtain all combinations of floors
floors_combinations= create_combinations(unique_floors)

#dict containing for each combination of floors the corresponding rooms/desks/zones
d_perm_rooms = concat_perm_rooms(dct, floors_combinations)
d_perm_desks = concat_perm_rooms(dct_desks, floors_combinations)
d_perm_zones = find_perm_zones(zones, floors_combinations)

#determine days for which optimizaiton should run by taking one day of old meeting bookings dataset frm Planon
all_days = sorted(data_optimization['Start'].dt.strftime('%Y-%m-%d').unique())[5:7] 

nr_employees= 40
days, intervals, teams, meetings, meeting_capacities, meeting_equipments, defactorized_equipments, df_optimization = generate_teams_and_reservations(nr_employees, data_optimization, all_days)

##########################Run scheduling algorithm ################################
succesful_combs= []
stop_after_first_solution = False
foundSolution=False
dct_combs= {}
all_viable_solutions={} # collects all succesful combinations and their allocations

# For all combinations of floors
for comb, rooms  in d_perm_rooms.items():
            if      foundSolution: 
                    break 
            else:
                    #per floor combination we obtain dictionary of rooms-capacities and rooms-equipments
                    dct_rooms_caps = find_capacities(rooms, data_optimization)
                    dct_rooms_eq = find_equipments(rooms,data_optimization, factorized=True)
                    dct_rooms_eq_plot = find_equipments(rooms,data_optimization, factorized=False)
                    
                    #returns list of all rooms, capacities and equipments specific to floor combination 
                    capacities_room = list(dct_rooms_caps.values())
                    total_rooms_ids = list(dct_rooms_caps.keys())
                    equipments_room = list(dct_rooms_eq.values())
                    try:
                            #only consider combinations that contain the ground floor '0'
                            if comb[0]=='0':
                                
                                #1. schedule all meetings
                                df, dct_team_floors= schedule_meetings(comb,intervals, days,total_rooms_ids, capacities_room,equipments_room,  df_optimization,dct_rooms_caps,dct_rooms_eq_plot,  teams, meetings ,meeting_capacities,meeting_equipments,defactorized_equipments, buffer_between_meetings=0, plot=True)
                                dct_combs[comb] = dct_team_floors
                                succesful_combs.append(comb)
                                
                                #2. schedule workspaces
                                zones_solution_found, allocation = allocate_teams_zones(comb, teams, zones, floors_combinations, dct_combs)
                                silents_solution_found, allocation_silents = allocate_silents(teams, comb, silent_zones)

                                if stop_after_first_solution & zones_solution_found & silents_solution_found: 
                                    foundSolution=True
                                    all_viable_solutions[comb]=allocation, allocation_silents
                                    
                                    # display final allocation
                                    disp_solution(all_viable_solutions, comb, days)
                                elif zones_solution_found & silents_solution_found:
                                    all_viable_solutions[comb]=allocation, allocation_silents
                                    print(all_viable_solutions)
                    except:
                             print('Optimal solution couldnt be found for comb: ' ,comb)
