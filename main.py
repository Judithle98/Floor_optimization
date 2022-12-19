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


from statistics import mode
# load data meeting reservations
data = pd.read_csv('Data/Data_Planon_Nijmegen.csv', sep=';')

# load data flex desk reservations
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
dct_desks = dct_floors_spaces(data_desks, desks= True)[0]
print(dct_desks)
## convert ito actual Des

zones = create_zones(data_desks)
# print zones!!
# for z in zones:
#     print('----------') 
#     print(z.name)
#     print(z.room)
#     print(z.floor)
#     print(z.equipments)
#     for d in z.desks:
#         print(d.name)


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

#team_names = np.array([fake.user_name() for i in range(10)])
teams = create_teams(departments, 2)


#teams = create_teams(departments,team_names)
employees= create_employees(nr_people,teams, fake)

if incl_equipments:
    data_optimization['new_Equipment'] = data_optimization['ResUnitName']
    equipments= np.unique(data_optimization['new_Equipment'])
    equipments_clean = [eq for eq in equipments if  eq!='(Beamer)' and  eq!='(Smartboard)' and eq!='(Tv screen)' ]

    for eq in equipments_clean:
        data_optimization['new_Equipment']= data_optimization['new_Equipment'].replace(eq, '')

    labels,uniques , data_optimization = factorize_equipment(data_optimization)
    
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
        
        print(employees[2].reservations)

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
                df =schedule_rooms(comb,intervals, all_days,days, total_rooms_ids, capacities_room,  data_optimization,dct_rooms_caps,employees, meetings, capacities_m, meeting_eq)      




#print(dct_team_floors)
reservation_caps = [] #per team capacities of desks required
reservation_equipments= []
e= []
for team in teams:
    print(team.name)
    equips = []
    # floor where the team has most meetings
    mode_floors = mode(dct_team_floors[team])
    # obtain all desks from that floor
    if mode_floors=='1':# no flex desks on floor 1
        mode_floors='2'
    desks= dct_desks[mode_floors]
    
    flex_res= list(team.desks_reservations())
    flex_desk_noSilent=[]
    for res in flex_res:
        print(res.equipment)
        if res.equipment !='silent':
            #check where the person has most meetings which floor & choose silent room on that floor
            flex_desk_noSilent.append(res)
            equips.append(res.equipment)
    reservation_caps.append(len(flex_desk_noSilent)) # capacity the number of flex desks reserved in a team
    reservation_equipments.append(equips)

    # floor where team has most meetings 
print(reservation_caps) 
print('---------------------')
print(reservation_equipments)



incl_zones=True
if incl_zones: 

##run scheduling algorithm for all floor combinations
    for comb, zones  in d_perm_zones.items(): 
            
            if comb == ('1', '2', '4'):
                #per floor combination find all available zones 
                dct_zones_caps = find_zone_capacities(zones)
                # print(dct_zones_caps)
                
                capacities_zones = list(dct_zones_caps.values()) # pick all capacities for reserved rooms for specific day [[3.0, 2.0, 3.0, 6.0, 8.0, 6.0]]
                # total_zone_ids = [z.name  for z in zones]
                # total_zone_ids=zones
                # print(total_zone_ids)
                equipments_zones= [z.equipments for z in zones ]
                #print(equipments_zones)
                df= schedule_desks(comb,zones, capacities_zones,equipments_zones,  dct_zones_caps,dct_rooms_eq,  teams, reservation_caps, reservation_equipments, plot=True)

               