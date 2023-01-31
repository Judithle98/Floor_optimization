import pandas as pd
from auxiliary_functions import *
from faker import Faker
import numpy as np

def preprocess_data(data, data_desks):

    # create seperate columns for date, start time, end time
    data['ResStartDate'] = data['ResStartDateTime'].str.split(' ').str[0]
    data['ResStartTime'] = data['ResStartDateTime'].str.split(' ').str[1]
    data['ResEndDate'] = data['ResEndDateTime'].str.split(' ').str[0]
    data['ResEndTime'] = data['ResEndDateTime'].str.split(' ').str[1]

    # Choose a subset of data
    data = data.dropna(subset=['ResUnitSpaceCategory'])
    data = data[(data['ResUnitSpaceCategory'] != 'Archived') & (data['ResUnitCapacity'] > 0)]
    data = data[data['ResUnitCode'] != 'NIJ REST']

    data_optimization = data
    data_optimization['Start time'] = data['ResStartTime'].str.split(':').str[0].astype(int)*60 + data['ResStartTime'].str.split(':').str[1].astype(int)
    data_optimization['Finish time'] = data['ResEndTime'].str.split(':').str[0].astype(int)*60 + data['ResEndTime'].str.split(':').str[1].astype(int)
    data_optimization['Capacities meeting'] = data_optimization['ResUnitCapacity']
    data_optimization['Day'] = pd.to_datetime(data_optimization['ResStartDate'])

    #make 2 new columns start and end
    data_optimization['Start'] = pd.to_datetime(data_optimization.ResStartDateTime)
    data_optimization['End'] = pd.to_datetime(data_optimization.ResEndDateTime)

    data_optimization = data_optimization[data_optimization['ResStartDate'] == data_optimization['ResEndDate']]
    data_optimization = data_optimization[(data_optimization['Finish time'] - data_optimization['Start time']) > 1]
    data_optimization = data_optimization.sort_values(by='Start', ascending=True)
    
    #create column with all floors
    data_optimization['Floor'] = create_floor_col(data_optimization)
      
    #create dict floor- meeting rooms
    dct, unique_floors= dct_floors_spaces(data_optimization)
    #create dict floor- desks
    dct_desks = dct_floors_spaces(data_desks, desks= True)[0]

    #create zones out of flex desks 
    zones, silent_zones = create_zones(data_desks)

    return data_optimization, dct, unique_floors,dct_desks, zones, silent_zones



#Function creates teams with randomly generates names and assigns teams to meeting reservations and creates flex desk reservations per team
# day: day for which LP runs
# intervals: time intervals
# teams: artificially generated teams
# meetings:list of  meetings ID (taken from real Planon dataset corresponding to specific day)
# meeting_capacities: list of corresponding meeting capacities 
# meeting_equipments: list of corresponding meeting equipments (factorized for LP)
# defactorized_equipments: list of corresponding equipments (de-factorized)
# df_optimization: dataframe of Planon dataset specific containing all meeting reservations for specific day
def generate_teams_and_reservations(nr_employees, data_optimization, all_days):
    fake=Faker()
    intervals = 20 # time intervals
    departments = ["sales","development", "marketing", 'IT']
    teams = create_teams(departments, 3)
    employees= create_employees(nr_employees,teams, fake)

    #clean the equipments in the dataset
    data_optimization['new_Equipment'] = data_optimization['ResUnitName']
    equipments= np.unique(data_optimization['new_Equipment'])
        
    # replace all non-equipments out of the column into an empty string
    equipments_clean = [eq for eq in equipments if  eq!='(Beamer)' and  eq!='(Smartboard)' and eq!='(Tv screen)' ]
    for eq in equipments_clean:
        data_optimization['new_Equipment']= data_optimization['new_Equipment'].replace(eq, None)
        
    #factorize equipments for LP to obtain numerical representation
    _, _, data_optimization = factorize_equipment(data_optimization)

    # assign teams to meeting reservations of Planon meeting data for specific day
    for day in enumerate(all_days):
        if day[0] == len(all_days)-1: # just to stop at the end
                break
        else:
            #obtain reservation list for specific day
            df_optimization = data_optimization[(data_optimization.Start >= f'{day[1]} 00:00:00') & (data_optimization.Start <= f'{all_days[day[0]+1]} 00:00:00')]
                        
            # create lists 
            meeting_capacities = df_optimization['Capacities meeting'].tolist() #list of all meeting capacities
            meeting_equipments= list(df_optimization["new_Equipment"])# list of factorized meeting equipments
            defactorized_equipments= list(df_optimization["Equipment"])        # only for plotting defactorized equipemnts later
            meetings= df_optimization['ResCode'] #list of meeting ids
            days = df_optimization['Start'].apply(lambda x: x.strftime('%Y-%m-%d')).unique()

            #create a Reservation object for meeting + desk reservations
            df_optimization, meeting_reservations = create_reservation_col(df_optimization, employees)
            desk_reservations= create_desks_reservations(employees)

            # assign reservations to specific employees (fake data)
            for e in employees:
                e.add_reservations(meeting_reservations)
                e.add_reservations(desk_reservations)
            
            #add all reservations per team
            for team in teams:
                    team.add_reservations()
                    team.add_equipments()

    return days, intervals, teams, meetings, meeting_capacities, meeting_equipments, defactorized_equipments, df_optimization 
 


