class Desk:
    def __init__(self, name, floor, equipment):
        self.name = name
        self.floor = floor
        self.zone=[]
        self.equipment= equipment
    
    
    def disp_short(self):
        return f"Desk: {self.name},with: {self.equipment}"