import random as rd
import numpy as np
from classes import Instance, Solution

nbRandomSols = 1
nbMaxIters = 100

class SolutionComplement:
    openStations: np.ndarray # [s] if station is open
    powerReceived: np.ndarray # [s, scen] is the power received by station s in scenario scen
    lossesInStat: np.ndarray # [s, scen] is the power loss at station s in scenario scen
    powerInStat: np.ndarray # [s, scen] is the power at station s in scenario scen
    lossesInStatCable: np.ndarray # [s, scen] is the power loss in cable between station s and on shore in scenario scen
    ### TAKE CARE OF FAILURES IN POWER RECEIVED
    lossesInStatStatCable: np.ndarray # [s1, s2, scen] is the power loss in cable between s1 and s2 in scenario scen in case of failure of s1

    def __init__(self, inst, sol) -> None:
        self.openStations = np.zeros((len(inst.stations)), dtype=int)
        self.powerReceived = np.zeros((len(inst.stations), len(inst.scenarios)), dtype=int)
        self.lossesInStat = np.zeros((len(inst.stations), len(inst.scenarios)), dtype=int)
        self.powerInStat = np.zeros((len(inst.stations), len(inst.scenarios)), dtype=int)
        self.lossesInStatCable = np.zeros((len(inst.stations), len(inst.scenarios)), dtype=int)
        self.lossesInStatStatCable = np.zeros((len(inst.stations), len(inst.stations), len(inst.scenarios)), dtype=int)
        for s in range(len(inst.stations)):
            stationType = np.argmax(sol.x[s, :]) if np.any(sol.x[s, :] == 1) else -1
            cableType = np.argmax(sol.y_off_on[s, :]) if np.any(sol.y_off_on[s, :] == 1) else -1
            if stationType == -1:
                continue
            self.openStations[s] = 1
            capacityStat = inst.substation_types[stationType].rating
            capacityCable = inst.land_to_sub_cables[cableType].rating
            for scen in range(len(inst.scenarios)):
                nbTurbines = sol.z[:, s].sum()
                self.powerReceived[s, scen] = nbTurbines * inst.scenarios[scen].power_generation
                self.powerInStat[s, scen] = min(self.powerReceived[s, scen], capacityStat)
                self.lossesInStat[s, scen] = self.powerReceived[s, scen] - self.powerInStat[s, scen]
                self.lossesInStatCable[s, scen] = max(self.powerInStat[s, scen] - capacityCable, 0)
        return None

def getRandomSol(inst):
    randomStations = []
    for i in range(len(inst.stations)):
        if (rd.randint(0, 1) == 0):
            randomStations.append(i)
    if len(randomStations) == 0:
        randomStations = [0]

    print("Choose stations ", randomStations)
    x = np.zeros((len(inst.stations), len(inst.substation_types)), dtype = int)
    yonoff = np.zeros((len(inst.stations), len(inst.land_to_sub_cables)), dtype = int)
    yoffoff = np.zeros((len(inst.stations), len(inst.stations), len(inst.land_to_sub_cables)), dtype = int)
    for randS in randomStations :
        x[randS, 0] = 1
        yonoff[randS, 0] = 1
    z = np.zeros((len(inst.turbines), len(inst.stations)), dtype=int)
    for t in range(len(inst.turbines)):
        bestS = randomStations[0]
        bestDist = inst.stations[bestS].distance(inst.turbines[t])
        for randS in randomStations:
            dist = inst.stations[randS].distance(inst.turbines[t])
            if (dist < bestDist) :
                dist = bestDist
                bestS = randS
        z[t, bestS] = 1
    return Solution(inst, x, yonoff, yoffoff, z)

def getNeighbor0(instance, initSol, solCplmt):
    # Neighbor : changer turbine vers autre station ouverte
    randTurbine = rd.randint(0, len(instance.turbines) - 1)

    currentSubstation = -1
    for s in range(len(instance.stations)):
        if initSol.z[randTurbine, s] == 1:
            currentSubstation = s
    if (currentSubstation == -1) :
        print("No current substation")
        return
    

    currentSubstationLoss = solCplmt.lossesInStat[currentSubstation, :].sum() + solCplmt.lossesInStatCable[currentSubstation, :].sum()
    stationType = np.argmax(initSol.x[currentSubstation, :]) if np.any(initSol.x[currentSubstation, :] == 1) else -1
    cableType = np.argmax(initSol.y_off_on[currentSubstation, :]) if np.any(initSol.y_off_on[currentSubstation, :] == 1) else -1
    currentCapacityStat = instance.substation_types[stationType].rating
    currentCapacityCable = instance.land_to_sub_cables[cableType].rating
    
    for s in range(len(instance.stations)):
        if s == currentSubstation or solCplmt.openStations[s] == 0:
            continue
        # Station is available : determine change cost
        diff = instance.variable_cost_cables * (instance.stations[currentSubstation].distance(instance.turbines[randTurbine]) - instance.stations[s].distance(instance.turbines[randTurbine]))
        nextSubstationLoss = solCplmt.lossesInStat[s, :].sum() + solCplmt.lossesInStat[s, :].sum()
        nextstationType = np.argmax(initSol.x[s, :]) if np.any(initSol.x[s, :] == 1) else -1
        nextcableType = np.argmax(initSol.y_off_on[s, :]) if np.any(initSol.y_off_on[s, :] == 1) else -1
        nextCapacityStat = instance.substation_types[nextstationType].rating
        nextCapacityCable = instance.land_to_sub_cables[nextcableType].rating
        for scen in range(len(instance.scenarios)):
            solCplmt.powerReceived[currentSubstation, scen] -= instance.scenarios[scen].power_generation
            solCplmt.powerReceived[s, scen] += instance.scenarios[scen].power_generation
            solCplmt.powerInStat[currentSubstation, scen] = min(solCplmt.powerReceived[currentSubstation, scen], currentCapacityStat)
            solCplmt.powerInStat[s, scen] = min(solCplmt.powerReceived[s, scen], nextCapacityStat)
            solCplmt.lossesInStat[s, scen] = solCplmt.powerReceived[s, scen] - solCplmt.powerInStat[s, scen]
            solCplmt.lossesInStatCable[s, scen] = max(solCplmt.powerInStat[s, scen] - nextCapacityCable, 0)
            solCplmt.lossesInStat[currentSubstation, scen] = solCplmt.powerReceived[currentSubstation, scen] - solCplmt.powerInStat[currentSubstation, scen]
            solCplmt.lossesInStatCable[currentSubstation, scen] = max(solCplmt.powerInStat[currentSubstation, scen] - currentCapacityCable, 0)
        diffLoss = currentSubstationLoss + nextSubstationLoss - solCplmt.lossesInStat[currentSubstation, :].sum() + solCplmt.lossesInStatCable[currentSubstation, :].sum() - solCplmt.lossesInStat[s, :].sum() + solCplmt.lossesInStatCable[s, :].sum()
        diff += instance.curtailing_cost * diffLoss
        if diff > 0:
            initSol.z[randTurbine, currentSubstation] = 0
            initSol.z[randTurbine, s] = 1
            return True, initSol
        else :
            solCplmt.powerReceived[currentSubstation, scen] += instance.scenarios[scen].power_generation
            solCplmt.powerReceived[s, scen] -= instance.scenarios[scen].power_generation
            solCplmt.powerInStat[currentSubstation, scen] = min(solCplmt.powerReceived[currentSubstation, scen], currentCapacityStat)
            solCplmt.powerInStat[s, scen] = min(solCplmt.powerReceived[s, scen], nextCapacityStat)
            solCplmt.lossesInStat[s, scen] = solCplmt.powerReceived[s, scen] - solCplmt.powerInStat[s, scen]
            solCplmt.lossesInStatCable[s, scen] = max(solCplmt.powerInStat[s, scen] - nextCapacityCable, 0)
            solCplmt.lossesInStat[currentSubstation, scen] = solCplmt.powerReceived[currentSubstation, scen] - solCplmt.powerInStat[currentSubstation, scen]
            solCplmt.lossesInStatCable[currentSubstation, scen] = max(solCplmt.powerInStat[currentSubstation, scen] - currentCapacityCable, 0)
    return False, initSol

def getNeighbor1(instance, initSol, solCplmt):
    # Neighbor : ouverture station
    if sum(solCplmt.openStations) >= 0.8 * len(solCplmt.openStations):
        return False, initSol
    randS = rd.randint(0, len(instance.stations) - 1)
    while solCplmt.openStations[randS] == 1:
        randS = rd.randint(0, len(instance.stations) - 1)

    solCplmt.openStations[randS] = 1
    for t in range(len(instance.turbines)):
        currentStation = np.argmax(initSol.z[t, :])
        if instance.stations[randS].distance(instance.turbines[t]) < instance.stations[randS].distance(instance.turbines[t]):
            #TODO
            return

    return

def getNeighbor2(instance, initSol, solCplmt):
    # Neighbor : swap station
    return

def getNeighbor3(instance, initSol, solCplmt):
    # Neighbor : changer type de cable
    return

def getNeighbor4(instance, initSol, solCplmt):
    # Neighbor : changer type de station
    return

def getNeighbor(instance, initSol, solCplmt, voisType):
    if (voisType < 0 or voisType > 4) :
        print("Error of neighborhoods")
        return
    if (voisType == 0):
        return getNeighbor0(instance, initSol, solCplmt)
    if (voisType == 1):
        return getNeighbor1(instance, initSol, solCplmt)
    if (voisType == 2):
        return getNeighbor2(instance, initSol, solCplmt)
    if (voisType == 3):
        return getNeighbor3(instance, initSol, solCplmt)
    if (voisType == 4):
        return getNeighbor4(instance, initSol, solCplmt)

def mainLSinst(instance):
    for rdSol in range(nbRandomSols):
        initSol = getRandomSol(instance)
        initSol.export_solution_json("huge_Try.json")
        solCplmt = SolutionComplement(instance, initSol)
        nbIters = -1
        while nbIters < nbMaxIters :
            nbIters += 1
            success, initSol = getNeighbor0(instance, initSol, solCplmt)
        initSol.export_solution_json("huge_Try_Fin.json")
            
        #print(initSol.z)
        #print(solCplmt.powerReceived)
        #print(solCplmt.lossesInStat)
        #print(solCplmt.powerInStat)
        #print(solCplmt.lossesInStatCable)
        """nbIter = -1
        nbIterWOSucc = 0
        voisType = 0
        while True:
            nbIter += 1
            success, initSol = getNeighbor(instance, initSol, voisType)
            if (success) :
                nbIterWOSucc = 0
                if (voisType == 4):
                    break
                voisType += 1
            else :
                nbIterWOSucc += 1
            if nbIterWOSucc > 50 :
                voisType += 1
                nbIterWOSucc = 0"""

def mainLS():
    return mainLSinst(Instance("./instances/huge.json"))

mainLS()
