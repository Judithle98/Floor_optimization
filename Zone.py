class Zone:
    def __init__(self, name, size, desks):
        self.name = name
        self.size=size
        self.floor = self.name[0]
        self.desks = desks
        self.equipment= add_equipments()

        def add_equipments(self):
            return [ d.equipment  for d in desks ]
    
    