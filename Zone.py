class Zone:
    def __init__(self, name,room,  size, desks):
        self.name = name
        self.room= room
        self.size=size
        self.desks = desks
        self.floor = self.room[0]
        self.equipments= self.add_equipments()

    def add_equipments(self):
       return [d.equipment  for d in self.desks ]


    def capacity(self):
        return len(self.desks)
    
    