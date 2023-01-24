import numpy as np
import pandas as pd
from auxiliary_functions import *
from schedule_equipment import schedule_rooms
from schedule_desks import schedule_desks
from faker import Faker

####################DATA#############
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

#################Preprocessing#########################

#create column with all floors
data_optimization['Floor'] = create_floor_col(data_optimization)

#create dict floor- meeting rooms
dct, unique_floors= dct_floors_spaces(data_optimization)
#create dict floor- desks
dct_desks = dct_floors_spaces(data_desks, desks= True)[0]

#create zones out of flex desks (idea: team is assigned to a zone except team member required privacy then team member is assigned to silent zone) 
zones, silent_zones = create_zones(data_desks)

#obtain all permutations of floors
floors_perm= create_perm(unique_floors)

#dict containing for each combination/permuation of floors the corresponding rooms/desks/zones
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
all_days = sorted(data_optimization['Start'].dt.strftime('%Y-%m-%d').unique())[5:7] 

#########################Employees #################### (fake data since this data is not available yet)
nr_people= 40
#departments = ["sales","development", "marketing", 'IT', "support", "HR"]
departments = ["sales","development", "marketing", 'IT']
teams = create_teams(departments, 3)
employees= create_employees(nr_people,teams, fake)

if incl_equipments:
    data_optimization['new_Equipment'] = data_optimization['ResUnitName']
    equipments= np.unique(data_optimization['new_Equipment'])
    
    # replace all non-equipments out of the column into an empty string
    equipments_clean = [eq for eq in equipments if  eq!='(Beamer)' and  eq!='(Smartboard)' and eq!='(Tv screen)' ]
    for eq in equipments_clean:
        data_optimization['new_Equipment']= data_optimization['new_Equipment'].replace(eq, None)
    
    #factorize equipments for LP
    labels, uniques, data_optimization = factorize_equipment(data_optimization)


##Create fake teams and assign them to reservations in df_optimization for specific day
for day in enumerate(all_days):
    if day[0] == len(all_days)-1: # just to stop at the end

             break
    else:
        #obtain reservation list for specific day
        df_optimization = data_optimization[(data_optimization.Start >= f'{day[1]} 00:00:00') & (data_optimization.Start <= f'{all_days[day[0]+1]} 00:00:00')]
                    
        # create lists 
        capacities_m = df_optimization['Capacities meeting'].tolist() #list of all meeting capacities
        meeting_eq= list(df_optimization["new_Equipment"])# list of factorized meeting equipments
        defac_meeting_eq= list(df_optimization["Equipment"])        # only for plotting defactorized equipemnts later
        meetings= df_optimization['ResCode'] #list of meeting ids
        days = df_optimization['Start'].apply(lambda x: x.strftime('%Y-%m-%d')).unique()

        #create a Reservation object for meeting + desk reservations
        df_optimization, meeting_reservations = create_reservation_col(df_optimization, employees)
        desk_reservations= create_desks_reservations(employees)

        # assign reservations to specific employees (fake data)
        for e in employees:
            e.add_reservations(meeting_reservations)
            e.add_reservations(desk_reservations)
        
        #add all reservations per team
        for team in teams:
                team.add_reservations()
                team.add_equipments()


##run scheduling algorithm for meeting rooms all floor combinations
succesful_combs= []

dct_combs= {}
for comb, rooms  in d_perm_rooms.items():
                #per floor combination we obtain dict of rooms-capacities and rooms-equipments
                dct_rooms_caps = find_capacities(rooms, data_optimization)
                dct_rooms_eq = find_equipments(rooms,data_optimization, factorized=True)
                dct_rooms_eq_plot = find_equipments(rooms,data_optimization, factorized=False)
                #belonging to this combination of floors, returns list of lal rooms, capacities and equipments
                capacities_room = list(dct_rooms_caps.values())
                total_rooms_ids = list(dct_rooms_caps.keys())
                equipments_room = list(dct_rooms_eq.values())

                if incl_equipments:
                    #for equipments
                    try:
                        df, dct_team_floors= schedule_rooms(comb,intervals,  days,total_rooms_ids, capacities_room,equipments_room,  df_optimization,dct_rooms_caps,dct_rooms_eq_plot,  teams, meetings ,capacities_m,meeting_eq,defac_meeting_eq, buffer_between_meetings=0, plot=True)
                        dct_combs[comb] = dct_team_floors
                        succesful_combs.append(comb)

                    except:
                        print('Optimal solution couldnt be found for comb: ' ,comb)
                else:
                    #no equipments
                    df =schedule_rooms(comb, intervals, all_days,days, total_rooms_ids, capacities_room,  data_optimization,dct_rooms_caps,employees, meetings, capacities_m)      


# solution_found, allocation= canBeAllocated_desks(('0', '1', '2'), teams, zones, floors_perm, dct_combs)
# print(solution_found)

solutions= {}
min_length= 2
if True:
 for comb in succesful_combs: 
#     #1.  floor 0 should always be included 
    if comb[0]=='0': # if ground floor is not included then remove comb
    #if comb== ('0', '1', '2'):
        zones_solution_found, allocation = canBeAllocated_desks(comb, teams, zones, floors_perm, dct_combs)
        silents_solution_found, allocation_silents = can_allocate_silents(teams, comb, silent_zones)
        print(zones_solution_found)
        print(silents_solution_found)

        if zones_solution_found: # and silents_solution_found:
        #if len(comb)<=min_length and solution_found:
            solutions[comb]=allocation, allocation_silents
        else: 
            solutions[comb]=[]

def disp_solution(comb, data_optimization):
    from IPython.display import display, HTML
    #check if the combination is actually a solution
    if comb in solutions.keys():
        ## obtain plot meetings 
        dct_rooms_caps = find_capacities(d_perm_rooms[comb], data_optimization)
        dct_rooms_eq = find_equipments(rooms,data_optimization, factorized=True)
        dct_rooms_eq_plot = find_equipments(rooms,data_optimization, factorized=False)
        #belonging to this combination of floors, returns list of lal rooms, capacities and equipments
        capacities_room = list(dct_rooms_caps.values())
        total_rooms_ids = list(dct_rooms_caps.keys())
        equipments_room = list(dct_rooms_eq.values())

        df_meetings, dct_team_floors= schedule_rooms(comb,intervals,  days,total_rooms_ids, capacities_room,equipments_room,  df_optimization,dct_rooms_caps,dct_rooms_eq_plot,  teams, meetings ,capacities_m,meeting_eq,defac_meeting_eq, buffer_between_meetings=0, plot=True)
        
        
        allocation, allocation_silents =solutions[comb]
        
        ############### Table final Silent Room allocations ####################
        df= pd.DataFrame()
        df['Employee']= [p.name for p in allocation_silents.keys()]
        df['Silent Room']= [ z.room  for z in allocation_silents.values()]
        df['Floor']= [ z.floor  for z in allocation_silents.values()]

        df['Employee requirement']= [res.equipment for p in allocation_silents.keys() for res in p.reservations if type(res)==FlexDeskReservation]
        df['Zone equipment']= [  z.equipments for z in allocation_silents.values()   ]
        df =df.style.set_caption(f'Allocations of Employees to Silent Rooms on the {days[0]} for floors: {comb}')
        display(HTML(df.to_html()))
        ############### Alocation non-silent flex desks ####################

        df_allocations= pd.DataFrame()
        #df_allocations['Team', 'Zone', 'Nr. Desk Reservations', 'Zone Capacity', 'Team requirements', 'Zone equipments'   ]
        df_allocations['Team'] = [t.name for t in allocation.keys() ]
        df_allocations['Zone'] = [z.name for z in allocation.values()]
        df_allocations['Floor'] = [z.floor for z in allocation.values()]
        df_allocations['Team desk reservations'] = [ len(t.equipments) for t in allocation.keys()]
        df_allocations['Zone Capacity '] = [z.size for z in allocation.values()]
        df_allocations['Team requirements']= [Counter(t.equipments) for t in allocation.keys()]
        df_allocations['Zone Equipments '] = [Counter(z.equipments) for z in allocation.values()]
        df_allocations= df_allocations.style.set_caption(f'Allocations of Teams to Zones on the {days[0]} for`floors: {comb} ')
        display(HTML(df_allocations.to_html()))


disp_solution(('0', '1', '3'), data_optimization)

# ##################### Table final Silent Room allocations ####################
df= pd.DataFrame()
df['Employee']= [p.name for p in allocation_silents.keys()]
df['Silent Room']= [ z.room  for z in allocation_silents.values()]
df['Floor']= [ z.floor  for z in allocation_silents.values()]

df['Employee requirement']= [res.equipment for p in allocation_silents.keys() for res in p.reservations if type(res)==FlexDeskReservation]
df['Zone equipment']= [  z.equipments for z in allocation_silents.values()   ]
df =df.style.set_caption(f'Allocations of Employees to Silent Rooms on the {days[0]} for floors: {comb}')

##################### Table final Silent Room allocations ####################


#df= pd.Dataframe(data, columns=['Team', 'Zone', 'Silent', 'Zone capacity'])

df_allocations= pd.DataFrame()
#df_allocations['Team', 'Zone', 'Nr. Desk Reservations', 'Zone Capacity', 'Team requirements', 'Zone equipments'   ]
df_allocations['Team'] = [t.name for t in allocation.keys() ]
df_allocations['Zone'] = [z.name for z in allocation.values()]
df_allocations['Floor'] = [z.floor for z in allocation.values()]
df_allocations['Team desk reservations'] = [ len(t.equipments) for t in allocation.keys()]
df_allocations['Zone Capacity '] = [z.size for z in allocation.values()]
df_allocations['Team requirements']= [Counter(t.equipments) for t in allocation.keys()]
df_allocations['Zone Equipments '] = [Counter(z.equipments) for z in allocation.values()]
df_allocations= df_allocations.style.set_caption(f'Allocations of Teams to Zones on the {days[0]} for`floors: {comb} ')


###???????team desk reservations


















