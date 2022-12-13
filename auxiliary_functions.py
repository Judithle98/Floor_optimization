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
from Reservation import MeetingReservation, FlexDeskReservation


## Helper functions

#creturns a list of all floors corresponding to different ResUnitCodes e.g. NIJ 2.14 will return 2
def create_floor_col(data, desks=False):
    data['Floor']=''
    list_floors = []
    if desks:
        column_name = 'Code'
        print(data['Code'])
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

## returns dict with Room:capactiy 
def find_capacities(rooms, data):
    dict_room_caps = dict.fromkeys(rooms)
    for room in rooms: 
        index= np.where(data["ResUnitCode"]==room)[0][0]
        dict_room_caps[room]=data.iloc[index]["ResUnitCapacity"]
    return dict_room_caps

# for equipments then delete later
def find_equipments(rooms, data):
    dict_room_eq= dict.fromkeys(rooms)
    for room in rooms: 
        index= np.where(data["ResUnitCode"]==room)[0][0]
        dict_room_eq[room]=data.iloc[index]["new_Equipment"]

    return dict_room_eq 

    
# turn equipments into numbers for LP constraints , all equipments of 0 are cancelled because otherwise
def factorize_equipment(df_optimization):

    labels, uniques = df_optimization['new_Equipment'].factorize()
    df_optimization['new_Equipment']= labels
    # replace all 0"s to 9"s simply bc otherwise linearizaton doesnt work
    #df_optimization['new_Equipment'] = df_optimization['new_Equipment'].replace(0, 9)

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
    requirements= ['silent', 'window', 'adjustable desk' ]
    reservations= []
    for e in employees:
        requirement= random.choice(requirements)
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
