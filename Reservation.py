class Reservation:
    def __init__(self,reserver,equipment):
        self.reserver = reserver
        self.equipment = equipment
  
class MeetingReservation(Reservation):
    def __init__(self,reserver,equipment, startTime,endTime, nr_members,members):
        super().__init__(reserver,equipment)
        self.startTime = startTime
        self.endTime = endTime
        self.nr_members = nr_members
        self.members = members

    def disp(self):
        return f"{self.reserver.disp_short()}, reserves from {self.startTime} to {self.endTime} needs {self.equipment} with {self.nr_members} people: {self.members}"

class FlexDeskReservation(Reservation):
    def __init__(self,reserver,equipment):
        super().__init__(reserver,equipment)
       

    def disp(self):
        return f"{self.reserver.disp_short()}, reserves flex desk and needs {self.equipment}"
