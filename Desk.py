class Desk:
    def __init__(self, name, floor, zone):
        self.name = name
        self.floor = floor
        self.zone=zone
        self.equipment= []
    
    
    def disp_short(self):
        return f"Desk: {self.name},with: {self.equipment}"