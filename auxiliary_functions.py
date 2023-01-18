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
from faker import Faker
from Person import Person
from Team import Team
from Desk import Desk
from Zone import Zone
import string
from Reservation import MeetingReservation, FlexDeskReservation
from collections import Counter
from statistics import mode

## Helper functions
#creturns a list of all floors corresponding to different ResUnitCodes e.g. NIJ 2.14 will return 2
def create_floor_col(data, desks=False):
    data['Floor']=''
    list_floors = []
    if desks:
        column_name = 'Code'
        [list_floors.append(data[column_name][i][0]) for i in data.index]
        return list_floors

    else:
        column_name = 'ResUnitCode'
        for i in data.index:
                list_floors.append(findFloor(data[column_name][i]))

        if len(list_floors)==data.shape[0]:
                try: 
                    return list_floors
                except: 
                    print("Floors could not be assigned") 

# returns dictionary Room: Floor as well as a list of unique floors
def dct_floors_spaces(data, desks= False):
    if desks: 

        column_name = 'Code'
        unique_floors = np.unique(data['Floor'])
        #create per list of desks per floor
        temp = dict(zip(data[column_name], data['Floor']))
        dct={}
        for f in unique_floors:

            dct['%s' % f]=([k for k,v in temp.items() if v==f])
   

    else: 
        column_name = 'ResUnitCode' 
        unique_rooms= np.unique(data[column_name])
        list_floors=[]
        for room in unique_rooms:
            list_floors.append(findFloor(room))

        dict_room_floors= dict(zip(unique_rooms,list_floors))
        unique_floors= np.unique(list(dict_room_floors.values()))
                 
        dct={}
        for f in unique_floors:
            dct['%s' % f]=([k for k,v in dict_room_floors.items() if v==f])
 
        
    return dct, unique_floors
    
def create_zones(data):
    zones= []
    zone_names= list(string.ascii_uppercase) + list(string.ascii_lowercase)+ [ ''.join(random.choice(string.ascii_uppercase) for i in range(2))  for i in range(100)]
    data['Zone'] = 0
    desk_rooms= data['Space.Space number']
    
    uniques, counts = np.unique(desk_rooms,return_counts=True)
 
    for i, room in enumerate(uniques):
        #find all indices with this room from data_desks
        indices = np.where(np.array(desk_rooms)==str(room))
    
        desks = [data.at[i, 'Code']  for i in indices[0]]
        if len(desks)==1:
             print(room)
        try: 
            sorted_indices= np.argsort([ int(d.split('-')[1]) for d in desks  ])
        except: 
            sorted_indices= np.argsort([ int(d.split('.')[1]) for d in desks   ])

        sorted_desks= list(np.array(desks)[sorted_indices]) # sorted desks with the assumption that flexdesj 3.04-01 is closer to 3.04-02 than 3.04-06
        equipments_desks= [ 'window', 'adjustable desk' ]
        sorted_desk_obj= [Desk(d,d[0], random.choice(equipments_desks)) for d in sorted_desks]
        if len(indices[0])<6:
            size=len(desks)
            zones.append(Zone(zone_names.pop(0), room, size, sorted_desk_obj))
            
        else: 
            sizes = [2,3,4,5,6,10] # possible zone sizes
            s = random.choice(sizes) 
            #create a zone of size s out of sorted flex desks 
            zones.append(Zone(zone_names.pop(0), room, s, sorted_desk_obj[:s] ))
            sorted_desk_obj = sorted_desk_obj[s:]
            while sorted_desk_obj!= []:
                sizes = [4,5,6,10]
                s = random.choice(sizes) 
                #create a zone of size s out of sorted flex desks 
                zones.append(Zone(zone_names.pop(0), room, s, sorted_desk_obj[:s] ))
                sorted_desk_obj = sorted_desk_obj[s:]
    silent_zones= [ z for z in zones if z.size==1]
    #add equipment 'silent for all silent zones'
    for z in silent_zones:
        z.equipments.append('silent')
    # remove all silent zones from zones
    for z in silent_zones:
        zones.remove(z) 
    
    return zones, silent_zones




#returns all permuations for unique floors
def create_perm(unique_floors):

    all_perm = list(itertools.permutations(unique_floors))

    all_perm = list()
    for n in range(len(unique_floors) + 1):
        all_perm += list(combinations(unique_floors, n))
    del all_perm[0]
    all_perm

    #convert to list
    permutations= []
    for perm in all_perm:
        permutations.append(tuple([e for e in perm]))
    return permutations


##creates a dict by concatentating all rooms per floors according to permutations
def concat_perm_rooms(dct, floors_perm): 
    dict_perm_rooms=dict.fromkeys(floors_perm,None)
    for perm in floors_perm:
        rooms=[]
        for floor in perm: # for individual floors in perm
            for k,v in dct.items():
                if floor==k:
                    for e in v: 
                        rooms.append(e)
        dict_perm_rooms[perm] =rooms     
    return dict_perm_rooms



def find_perm_zones(zones, floors_perm):
    dct_perm_zones=dict.fromkeys(floors_perm,[])
    for perm in floors_perm:
        zs=[]
        for floor in perm:
            for zone in zones:
              
                if zone.floor==floor:

                    zs.append(zone)
        dct_perm_zones[perm] = zs 

    return dct_perm_zones

#returns dict per zone the capacity 
def find_zone_capacities(zones):
    dct_zone_caps= dict.fromkeys(zones) 
    for z in zones:
        dct_zone_caps[z]= z.capacity()
    return dct_zone_caps


## returns dict with Room:capactiy 
def find_capacities(rooms, data):
    dict_room_caps = dict.fromkeys(rooms)
    for room in rooms: 
        index= np.where(data["ResUnitCode"]==room)[0][0]
        dict_room_caps[room]=data.iloc[index]["ResUnitCapacity"]
    return dict_room_caps

# for equipments then delete later
def find_equipments(rooms, data, factorized=False):
    dict_room_eq= dict.fromkeys(rooms)
    for room in rooms: 
        index= np.where(data["ResUnitCode"]==room)[0][0]
        if factorized==True:
            dict_room_eq[room]=data.iloc[index]["new_Equipment"]
        else:
            dict_room_eq[room]=data.iloc[index]["Equipment"]

    return dict_room_eq 

    
# turn equipments into numbers for LP constraints , all equipments of 0 are cancelled because otherwise
def factorize_equipment(df_optimization):

    labels, uniques = df_optimization['new_Equipment'].factorize()
    df_optimization['Equipment']= uniques[labels]
    df_optimization['new_Equipment']= labels
 
    return labels, uniques, df_optimization


def create_employees(nr_people, teams,fake):
    #Generate employees
    employees = []
    for i in range(0,nr_people):
        name = fake.name()
        #department = random.choice(departments)
        #teamsdep = teams[departments.index(department)]
        team = random.choice(teams)
        department = team.department
        #team= np.random.choice(teamsdep)
        #person = Person(name,department,team,None)
        person = Person(name,department,team)

        team.members.append(person)
        employees.append(person)
    return employees

def create_teams(departments, teams_per_dep):
    fake=Faker()
    teams= []
    team_names = [fake.user_name() for i in range(10)]
    for dep in departments:
        # nr. of teams per department 
        nr_teams =np.random.randint(1,teams_per_dep) 
        for i in range(nr_teams): 
            name = team_names[0]
            team_names.pop(0)
            team = Team(name, dep)
            teams.append(team)
    return teams


def create_reservation_col(data, employees):
    for i,row in data.iterrows():
        reserver= random.choice(employees)
        nr_members= int(data.at[i,'ResUnitCapacity'])
        equipment=  data.at[i,'new_Equipment']
        #everyone except reserver him/herself
        employees_excl_self=[e for e in employees if e!=employees]
        members = random.sample(employees_excl_self,nr_members)
        start =  data.at[i,'Start']
        end =  data.at[i,'End']
        reservation = MeetingReservation(reserver,equipment, start,end, nr_members, members )
        data.at[i,'Reservation'] = reservation
    reservations = data['Reservation'].tolist()
    return data, reservations

def create_desks_reservations(employees):
    requirements= ['silent', 'window', 'adjustable desk'  ]
    reservations= []
    for e in employees:
        
        requirement= random.choice(requirements)
        if requirement=='silent': 
            req_excl_silent= requirements.copy()
            req_excl_silent.remove('silent')
            nr_additional_requirements= random.randint(0,1)
            if nr_additional_requirements>0:
                requirement2= random.choice(req_excl_silent)
                equips=[requirement, requirement2]
                reservations.append(FlexDeskReservation(e, equips))
            else: 
                reservations.append(FlexDeskReservation(e, requirement))
        else: 
            reservations.append(FlexDeskReservation(e, requirement))
    return reservations



def p_most_meetings_per_team(teams, employees, reservations):
    dict_team_members = dict.fromkeys(teams, 0)
    dict_team_most_meetings = dict.fromkeys(teams, 0)
    dict_team_members
    for team in teams: 
        dict_team_members[team] = team.members
        #nr_meetings_team= len(team.reservations)
        dict_team_most_meetings[team] = team.most_meetings(), len(team.most_meetings().reservations)
    return dict_team_most_meetings, dict_team_members

# function adds all reservations in which employee is included to the Person class
def add_p_reservations(reservations, employees):
    
    for e in employees:
        e.reservations= [res for res in reservations if e==res.reserver or e in res.members]

# function returns floor to specific room
def findFloor(room):
    if ' ' in room:
        return room.split(' ')[1][:1]
    else:
        return room.split('-')[1][:1]



def canBeAllocated_desks(final_comb, teams, zones, floors_perm, dct_combs):
    #final allocation of teams to zones
    assignments_team_zones= dict.fromkeys(teams, 0)
    allAssigned=False
    ##filter out the silent flex desk reservations 
    dct_team_deskres= dict.fromkeys(teams,0)
    for team in teams:
        flex_res= []
        for res in team.desks_reservations():
            if 'silent' not in res.equipment:
            #if res.equipment!='silent':
                flex_res.append(res)
        
        dct_team_deskres[team]=flex_res, team.equipments

    teams_notAssigned=teams.copy()
    d_perm_zones = find_perm_zones(zones, floors_perm)

    for team in teams_notAssigned: 
        #capacity of team without people that sit in silent room
        team_cap = len(dct_team_deskres[team][0])
        #floor where team has most meetings
        if dct_combs[final_comb][team]!=[]: # just added this
            mode_floor = mode(dct_combs[final_comb][team])

        zones_mostMeetings= d_perm_zones[tuple(mode_floor)]
        l=  list(final_comb)
        l.remove(mode_floor)
        zones_diffFloors = d_perm_zones[tuple(l)]
        
        # loop through all zones on the floor where the team has the most meetings
        for z in zones_mostMeetings:
            if assignments_team_zones[team]!=0:
                break
            #Case 1: size of the zone exactly equals capacity of the team, zone includes all equipments that the team requires, zone is on foor where team has most meetings
            if  (z.size==team_cap) and (not Counter(dct_team_deskres[team][1])- Counter(z.equipments)) and (z.floor==mode_floor): 
                assignments_team_zones[team] = z
                zones_mostMeetings.remove(z) # no other team can be assigned to this zone

        for z in zones_mostMeetings:
            if assignments_team_zones[team]!=0:
                break
            #Case 2: size of the zone is larger than capacity of the team, zone includes all equipments that the team requires, zone is on foor where team has most meetings
            if (z.size>=team_cap) and (not Counter(dct_team_deskres[team][1])- Counter(z.equipments)) and (z.floor==mode_floor): 
                assignments_team_zones[team] = z
                zones_mostMeetings.remove(z) # no other team can be assigned to this zone
               # print(f"Team: {team.name} with {team_cap} members and requirements {team.equipments} is assigned to zone: {z.name} of size {z.size} on floor {z.floor} with equipments: {z.equipments}")

        if assignments_team_zones[team]==0:

            #Case 3: size of the zone equals capacity of the team,  includes all equipments that the team requires, zone is on differnt floor where team has most meetings
            for z in zones_diffFloors:
                if assignments_team_zones[team]!=0:
                    break
                if  (z.size==team_cap) and (not Counter(dct_team_deskres[team][1])- Counter(z.equipments)): 
                    assignments_team_zones[team] = z
                    zones_diffFloors.remove(z) # no other team can be assigned to this zone
             #Case 4: size of the zone larger than capacity of the team,  includes all equipments that the team requires, zone is on differnt floor where team has most meetings

            for z in zones_diffFloors:
                if assignments_team_zones[team]!=0:
                    break
                if (z.size>=team_cap) and (not Counter(dct_team_deskres[team][1])- Counter(z.equipments)) : 
                    assignments_team_zones[team] = z
                    zones_diffFloors.remove(z) # no other team can be assigned to this zone
                   
    if not 0 in assignments_team_zones.values():
        allAssigned=True

    return allAssigned, assignments_team_zones



# function checks if all employees that required a silent room can be allocated to one
# # returns true if enough silent rooms are available + corresponding allocation 
def can_allocate_silents(teams, comb, silent_zones): 
    available_zones= [z for z in silent_zones if z.floor in comb]
    solution_found= False
    silent_reservations=[]
    #for all teams add up the reservations that require a silent room
    teams_notAssigned=teams.copy()
    for t in teams: 
        silent_reservations.append(t.silent_res)
    flattened = [val for sublist in silent_reservations for val in sublist]
    allocation_silentRooms= dict.fromkeys([res.reserver for res in flattened], 0)

    for res in flattened: 
            for z in available_zones:
                if allocation_silentRooms[res.reserver]!=0:
                    break
                #Case 1: size of the zone exactly equals capacity of the team, zone includes all equipments that the team requires, zone is on foor where team has most meetings
                if type(res.equipment)!=list:
                        equip = [res.equipment]
                else: 
                    equip = res.equipment
    
                if  Counter(equip)== Counter(z.equipments): 
                        allocation_silentRooms[res.reserver] = z
                        available_zones.remove(z) # no other team can be assigned to this zone
                        
            if allocation_silentRooms[res.reserver]==0:
                for z in available_zones: 
                    if allocation_silentRooms[res.reserver]!=0:
                        break
                    if type(res.equipment)!=list:
                            equip = [res.equipment]
                    else: 
                        equip = res.equipment
                
                    if  not( Counter(equip)- Counter(z.equipments)):
                            allocation_silentRooms[res.reserver] = z
                            available_zones.remove(z) # no other team can be assigned to this zone
                          
    if not 0 in allocation_silentRooms.values():
            solution_found=True
            print('solution found') 
            return solution_found, allocation_silentRooms
    else: 
        print('No solution found for silents')
        return solution_found, allocation_silentRooms
#  
# def can_allocate_silents(teams, comb, silent_zones): 
#     solution_found= False
#     silent_reservations=[]
#     #for all teams add up the reservations that require a silent room
#     for t in teams: 
#         silent_reservations.append(t.silent_res)
#     flattened = [val for sublist in silent_reservations for val in sublist]
#     #filter out only silent rooms of specific floor comb
#     available_zones= [z for z in silent_zones if z.floor in comb]
#     if len(silent_reservations)<= len(available_zones): 
#         allocation_silentRooms= dict(zip(silent_zones, [ res.reserver for res in flattened]))
#         solution_found=True
#         return solution_found, allocation_silentRooms


def disp_allocation(solutions, dct_combs): 
    for comb, allocation in solutions.items(): 

      
        print('---------------------------')

        if allocation==[]: 
            print('Employees could not be assigned zones on floors: ',comb )
        else: 
            for team, zone in allocation[0].items(): 

                mode_floor=  mode(dct_combs[comb][team])
                if zone.floor==mode_floor:
                    print(f"Team: {team.name} with {len(team.equipments)} members and requirements {team.equipments} is assigned to zone: {zone.name} of size {zone.size} on floor {zone.floor} with equipments: {zone.equipments} on floor where it has most meetings")
                else: 
                    print(f"Team: {team.name} with {len(team.equipments)} members and requirements {team.equipments} is assigned to zone: {zone.name} of size {zone.size} on floor {zone.floor} with equipments: {zone.equipments}")

