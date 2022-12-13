#from auxiliary_functions import *
import auxiliary_functions as ax
#import auxiliary_functions as ax
import numpy as np

class Team:
    def __init__(self, name, department):
        self.name = name
        self.department = department
        self.members=[]
        self.reservations = []
     
    
        
    def disp(self):
        return f"Team: {self.name} from {self.department} and has members: {self.members.disp_short()}"
    
    def disp_short(self):
        return f"{self.name}"


    def add_reservations(self): 
        for p in self.members: 
            for res in p.reservations: 
                self.reservations.append(res)
        #self.reservations= [p.reservations for p in self.members]

    def most_meetings(self):
        counts= []
        [counts.append(len(mem.reservations)) for mem in self.members]
        max_index=counts.index(max(counts))
        return self.members[max_index]

    

    def floors_reservations(self, dct_room_res): 
        floors = []
        for res in self.reservations: 
            for k,v in dct_room_res.items():
                if res in v:
                    floors.append(ax.findFloor(k))
        return floors