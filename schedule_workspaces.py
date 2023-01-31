from auxiliary_functions import *
## this file contains all functions to schedule workspaces and display the final allocation



def allocate_teams_zones(final_comb, teams, zones, floors_perm, dct_combs):
    assignments_team_zones= dict.fromkeys(teams, 0)
    allAssigned=False
    ##filter out the silent flex desk reservations 
    dct_team_deskres= dict.fromkeys(teams,0)
    for team in teams:
        flex_res= []
        for res in team.desks_reservations():
            if 'silent' not in res.equipment:
                flex_res.append(res)
        
        dct_team_deskres[team]=flex_res, team.equipments

    teams_notAssigned=teams.copy()
    d_perm_zones = find_perm_zones(zones, floors_perm)

    for team in teams_notAssigned: 
        #capacity of team without people that sit in silent room
        team_cap = len(dct_team_deskres[team][0])
        #floor where team has most meetings
        if dct_combs[final_comb][team]!=[]: 
            mode_floor = mode(dct_combs[final_comb][team])

        zones_mostMeetings= d_perm_zones[tuple(mode_floor)]
        l=  list(final_comb)
        l.remove(mode_floor)
        zones_diffFloors = d_perm_zones[tuple(l)]
        
        # loop through all zones on the floor where the team has the most meetings
        for z in zones_mostMeetings:
            if assignments_team_zones[team]!=0:
                break
            #Case 1: size of the zone exactly equals capacity of the team, zone includes all equipments that the team requires, zone is on foor where team has most meetings
            if  (z.size==team_cap) and (not Counter(dct_team_deskres[team][1])- Counter(z.equipments)) and (z.floor==mode_floor): 
                assignments_team_zones[team] = z
                zones_mostMeetings.remove(z) # no other team can be assigned to this zone

        for z in zones_mostMeetings:
            if assignments_team_zones[team]!=0:
                break
            #Case 2: size of the zone is larger than capacity of the team, zone includes all equipments that the team requires, zone is on foor where team has most meetings
            if (z.size>=team_cap) and (not Counter(dct_team_deskres[team][1])- Counter(z.equipments)) and (z.floor==mode_floor): 
                assignments_team_zones[team] = z
                zones_mostMeetings.remove(z) # no other team can be assigned to this zone
               # print(f"Team: {team.name} with {team_cap} members and requirements {team.equipments} is assigned to zone: {z.name} of size {z.size} on floor {z.floor} with equipments: {z.equipments}")

        if assignments_team_zones[team]==0:

            #Case 3: size of the zone equals capacity of the team,  includes all equipments that the team requires, zone is on differnt floor where team has most meetings
            for z in zones_diffFloors:
                if assignments_team_zones[team]!=0:
                    break
                if  (z.size==team_cap) and (not Counter(dct_team_deskres[team][1])- Counter(z.equipments)): 
                    assignments_team_zones[team] = z
                    zones_diffFloors.remove(z) # no other team can be assigned to this zone
             #Case 4: size of the zone larger than capacity of the team,  includes all equipments that the team requires, zone is on differnt floor where team has most meetings

            for z in zones_diffFloors:
                if assignments_team_zones[team]!=0:
                    break
                if (z.size>=team_cap) and (not Counter(dct_team_deskres[team][1])- Counter(z.equipments)) : 
                    assignments_team_zones[team] = z
                    zones_diffFloors.remove(z) # no other team can be assigned to this zone
                   
    if not 0 in assignments_team_zones.values():
        allAssigned=True

    return allAssigned, assignments_team_zones

# function checks if all employees that required a silent room can be allocated to one
# # returns true if enough silent rooms are available + corresponding allocation 
def allocate_silents(teams, comb, silent_zones): 
    available_zones= [z for z in silent_zones if z.floor in comb]
    solution_found= False
    silent_reservations=[]
    #for all teams add up the reservations that require a silent room
    teams_notAssigned=teams.copy()
    for t in teams: 
        silent_reservations.append(t.silent_res)
    flattened = [val for sublist in silent_reservations for val in sublist]
    allocation_silentRooms= dict.fromkeys([res.reserver for res in flattened], 0)

    for res in flattened: 
            for z in available_zones:
                if allocation_silentRooms[res.reserver]!=0:
                    break
                if type(res.equipment)!=list:
                        equip = [res.equipment]
                else: 
                    equip = res.equipment
    
                if  Counter(equip)== Counter(z.equipments): 
                        allocation_silentRooms[res.reserver] = z
                        available_zones.remove(z) # no other team can be assigned to this zone
                        
            if allocation_silentRooms[res.reserver]==0:
                for z in available_zones: 
                    if allocation_silentRooms[res.reserver]!=0:
                        break
                    if type(res.equipment)!=list:
                            equip = [res.equipment]
                    else: 
                        equip = res.equipment
                
                    if  not( Counter(equip)- Counter(z.equipments)):
                            allocation_silentRooms[res.reserver] = z
                            available_zones.remove(z) # no other team can be assigned to this zone
                          
    if not 0 in allocation_silentRooms.values():
            solution_found=True
            return solution_found, allocation_silentRooms
    else: 
        return solution_found, allocation_silentRooms

#function displays the the final allocation fo workspaces for one floor combination
#returns one table with allocation of teams to zones and one with allocation of employees to silent rooms
def disp_solution(solutions,comb, days):
    
    #check if the combination is actually a solution
    if comb in solutions.keys():

        allocation, allocation_silents =solutions[comb]
        
        ############### Table final Silent Room allocations ####################
        df= pd.DataFrame()
        df['Employee']= [p.name for p in allocation_silents.keys()]
        df['Silent Room']= [ z.room  for z in allocation_silents.values()]
        df['Floor']= [ z.floor  for z in allocation_silents.values()]

        df['Employee requirement']= [res.equipment for p in allocation_silents.keys() for res in p.reservations if type(res)==FlexDeskReservation]
        df['Zone equipment']= [  z.equipments for z in allocation_silents.values()   ]
        df =df.style.set_caption(f'Allocations of Employees to Silent Rooms on the {days[0]} for floors: {comb}')
        display(HTML(df.to_html()))
        ############### Alocation non-silent flex desks ####################

        df_allocations= pd.DataFrame()
        #df_allocations['Team', 'Zone', 'Nr. Desk Reservations', 'Zone Capacity', 'Team requirements', 'Zone equipments'   ]
        df_allocations['Team'] = [t.name for t in allocation.keys() ]
        df_allocations['Zone'] = [z.name for z in allocation.values()]
        df_allocations['Floor'] = [z.floor for z in allocation.values()]
        df_allocations['Team desk reservations'] = [ len(t.equipments) for t in allocation.keys()]
        df_allocations['Zone Capacity '] = [z.size for z in allocation.values()]
        df_allocations['Team requirements']= [Counter(t.equipments) for t in allocation.keys()]
        df_allocations['Zone Equipments '] = [Counter(z.equipments) for z in allocation.values()]
        df_allocations= df_allocations.style.set_caption(f'Allocations of Teams to Zones on the {days[0]} for`floors: {comb} ')
        display(HTML(df_allocations.to_html()))


