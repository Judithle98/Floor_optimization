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
def dct_rooms_floor(data):
    unique_meeting_rooms= np.unique(data['ResUnitCode'])
    rooms_per_floor= []
    list_floors=[]
    for room in unique_meeting_rooms:
        if ' ' in room:
            list_floors.append(room.split(' ')[1][:1])
        else:
            list_floors.append(room.split('-')[1][:1])

    dict_room_floors= dict(zip(unique_meeting_rooms,list_floors))
    unique_floors= np.unique(list(dict_room_floors.values()))

    dct={}
    for f in unique_floors:
        dct['%s' % f]=([k for k,v in dict_room_floors.items() if v==f])
    
    return dct,unique_floors

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