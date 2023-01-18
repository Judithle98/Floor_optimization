#from auxiliary_functions import *
import auxiliary_functions as ax
from Reservation import FlexDeskReservation
import numpy as np
from statistics import mode

class Team:
    def __init__(self, name, department):
        self.name = name
        self.department = department
        self.members=[]
        self.reservations = []
        self.equipments= []
        self.silent_res =[]
        self.mode=-1
     
    
        
    def disp(self):
        return f"Team: {self.name} from {self.department} and has members: {self.members.disp_short()}"
    
    def disp_short(self):
        return f"{self.name}"

    #adds up reservations of all team members into self.reservations
    def add_reservations(self): 
        for p in self.members: 
            for res in p.reservations: 
                self.reservations.append(res)
       
    #returns member with the most meetings
    def most_meetings(self):
        counts= []
        [counts.append(len(mem.reservations)) for mem in self.members]
        max_index=counts.index(max(counts))
        return self.members[max_index]
    
    #returns all flex desk reservations of the team (silent + not silent)
    def desks_reservations(self):
        return  [res  for res in self.reservations if isinstance(res, FlexDeskReservation)]

    #returns the floor of each reservation to calculate the mode
    def floors_reservations(self, dct_room_res): 
        floors = []
        for res in self.reservations: 
            for k,v in dct_room_res.items():
                if res in v:
                    floors.append(ax.findFloor(k))

        return floors
    #adds up all equipments of the flex desk reservation excluding the silent requirements
    def add_equipments(self):
  
        for res in self.desks_reservations():
            if 'silent' not in res.equipment:
                self.equipments.append(res.equipment)
            else:
                self.silent_res.append(res)

            # if res.equipment!='silent':
            #     self.equipments.append(res.equipment)
            # else:
            #     self.silent_res.append(res)
