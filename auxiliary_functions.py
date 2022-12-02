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


## Helper functions

#creturns a list of all floors corresponding to different ResUnitCodes e.g. NIJ 2.14 will return 2
def create_floor_col(data):
    data['Floor']=''
    list_floors = []
    for i in data.index:
        if ' ' in data['ResUnitCode'][i]:
            list_floors.append(data['ResUnitCode'][i].split(' ')[1][:1])
        else:
            list_floors.append(data['ResUnitCode'][i].split('-')[1][:1])

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
        rooms_per_floor= []
        list_floors=[]
        for room in unique_rooms:
            if ' ' in room:
                list_floors.append(room.split(' ')[1][:1])
            else:
                list_floors.append(room.split('-')[1][:1])

        dict_room_floors= dict(zip(unique_rooms,list_floors))
        unique_floors= np.unique(list(dict_room_floors.values()))
                 
        dct={}
        for f in unique_floors:
            dct['%s' % f]=([k for k,v in dict_room_floors.items() if v==f])
        
    return dct

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
    for perm in floors_perm: # [0],[1],[2],[3],[0,1,2,3,4]
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


def create_employees(nr_people,departments, teams,fake):
    #Generate employees
    employees = []
    for i in range(0,nr_people):
        name = fake.name()
        department = random.choice(departments)
        teamsdep = teams[departments.index(department)]

        team= np.random.choice(teamsdep)
        person = Person(name,department,team,None)
        employees.append(person)
    return employees


def create_teams(departments,team_names):
    teams= []
    for dep in departments:
        # nr. of teams within department , usually maybe 3 i stick to two now
        nr_teams =np.random.randint(1,2) 
        names = team_names[:nr_teams]
        team_names = team_names[nr_teams:]
        teams.append(names)
    return teams

#def most_meetings():

