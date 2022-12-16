from Reservation import MeetingReservation
class Person:
    def __init__(self, name, department,team):
        self.name = name
        self.department = department
        self.team=team
        self.reservations= []
    
        
    def disp(self):
        return f"{self.name} from {self.department} and team: {self.team.disp_short()}"
    
    def disp_short(self):
        return f"{self.name}, {self.department}"
    
    def add_reservations(self, reservations):
        # for e in employees:
        #     e.reservations= [res for res in reservations if e==res.reserver or e in res.members]
        for res in reservations: 
            if  isinstance(res, MeetingReservation):
                 if self==res.reserver or self in res.members:
                     self.reservations.append(res)
            else: #flex desk 
                 if self==res.reserver:
                     self.reservations.append(res)
                     