class Person:
    def __init__(self, name, department,team, reservations):
        self.name = name
        self.department = department
        self.team=team
        self.reservations= reservations
    
        
    def disp(self):
        return f"{self.name} from {self.department} and team: {self.team.disp_short()}"
    
    def disp_short(self):
        return f"{self.name}, {self.department}"
    
