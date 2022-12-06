class Reservation:
    def __init__(self,reserver,equipment,day):
        self.reserver = reserver
        self.equipment = equipment
        self.day=day
  
class MeetingReservation(Reservation):
    def __init__(self,reserver,equipment,day, startTime,endTime, nr_members,members):
        super().__init__(reserver,equipment,day)
        self.startTime = startTime
        self.endTime = endTime
        self.nr_members = nr_members
        self.members = members

    def disp(self):
        return f"{self.reserver.disp_short()}, reserves on {self.day} from {self.startTime} to {self.endTime} needs {self.equipment} with {self.nr_members} people: {self.members}"
