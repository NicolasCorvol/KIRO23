import random as rd
import numpy as np
from classes import Instance, Solution
from copy import deepcopy

nbRandomSols = 1
nbMaxIters = 5000

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
        diffLoss = currentSubstationLoss - nextSubstationLoss
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

def getNeighbor3(instance, initSol, solCplmt):
    # Neighbor : ouverture station
    if sum(solCplmt.openStations) >= 0.8 * len(solCplmt.openStations) or solCplmt.lossesInStat.sum() == 0:
        return False, initSol
    randS = rd.randint(0, len(instance.stations) - 1)
    while solCplmt.openStations[randS] == 1:
        randS = rd.randint(0, len(instance.stations) - 1)

    solCplmtCopy = deepcopy(solCplmt)
    
    turbinesToChange = []

    solCplmt.openStations[randS] = 1
    randCableType = rd.randint(0, len(instance.land_to_sub_cables) - 1)
    randStatType = rd.randint(0, len(instance.substation_types) - 1)
    initSol.x[randS, randStatType] = 1
    initSol.y_off_on[randS, randCableType] = 1
    diff = - instance.substation_types[randStatType].cost


    for t in range(len(instance.turbines)):
        currentStation = np.argmax(initSol.z[t, :])
        currentSubstationLoss = solCplmt.lossesInStat[currentStation, :].sum() + solCplmt.lossesInStatCable[currentStation, :].sum()
        stationType = np.argmax(initSol.x[currentStation, :]) if np.any(initSol.x[currentStation, :] == 1) else -1
        cableType = np.argmax(initSol.y_off_on[currentStation, :]) if np.any(initSol.y_off_on[currentStation, :] == 1) else -1
        currentCapacityStat = instance.substation_types[stationType].rating
        currentCapacityCable = instance.land_to_sub_cables[cableType].rating
        if instance.stations[randS].distance(instance.turbines[t]) < instance.stations[randS].distance(instance.turbines[t]) or solCplmt.lossesInStat[currentStation, :].sum() > 0:
            diffLoc = instance.variable_cost_cables * (instance.stations[currentStation].distance(instance.turbines[t]) - instance.stations[randS].distance(instance.turbines[t]))
            nextSubstationLoss = solCplmt.lossesInStat[randS, :].sum() + solCplmt.lossesInStat[randS, :].sum()
            nextstationType = np.argmax(initSol.x[randS, :]) if np.any(initSol.x[randS, :] == 1) else -1
            nextcableType = np.argmax(initSol.y_off_on[randS, :]) if np.any(initSol.y_off_on[randS, :] == 1) else -1
            nextCapacityStat = instance.substation_types[nextstationType].rating
            nextCapacityCable = instance.land_to_sub_cables[nextcableType].rating
            for scen in range(len(instance.scenarios)):
                solCplmt.powerReceived[currentStation, scen] -= instance.scenarios[scen].power_generation
                solCplmt.powerReceived[randS, scen] += instance.scenarios[scen].power_generation
                solCplmt.powerInStat[currentStation, scen] = min(solCplmt.powerReceived[currentStation, scen], currentCapacityStat)
                solCplmt.powerInStat[randS, scen] = min(solCplmt.powerReceived[randS, scen], nextCapacityStat)
                solCplmt.lossesInStat[randS, scen] = solCplmt.powerReceived[randS, scen] - solCplmt.powerInStat[randS, scen]
                solCplmt.lossesInStatCable[randS, scen] = max(solCplmt.powerInStat[randS, scen] - nextCapacityCable, 0)
                solCplmt.lossesInStat[currentStation, scen] = solCplmt.powerReceived[currentStation, scen] - solCplmt.powerInStat[currentStation, scen]
                solCplmt.lossesInStatCable[currentStation, scen] = max(solCplmt.powerInStat[currentStation, scen] - currentCapacityCable, 0)
            diffLoss = currentSubstationLoss + nextSubstationLoss - solCplmt.lossesInStat[currentStation, :].sum() + solCplmt.lossesInStatCable[currentStation, :].sum() - solCplmt.lossesInStat[randS, :].sum() + solCplmt.lossesInStatCable[randS, :].sum()
            diffLoc += instance.curtailing_cost * diffLoss
            if diffLoc > 0:
                turbinesToChange.append(t)
                diff += diffLoc
            else :
                solCplmt.powerReceived[currentStation, scen] += instance.scenarios[scen].power_generation
                solCplmt.powerReceived[randS, scen] -= instance.scenarios[scen].power_generation
                solCplmt.powerInStat[currentStation, scen] = min(solCplmt.powerReceived[currentStation, scen], currentCapacityStat)
                solCplmt.powerInStat[randS, scen] = min(solCplmt.powerReceived[randS, scen], nextCapacityStat)
                solCplmt.lossesInStat[randS, scen] = solCplmt.powerReceived[randS, scen] - solCplmt.powerInStat[randS, scen]
                solCplmt.lossesInStatCable[randS, scen] = max(solCplmt.powerInStat[randS, scen] - nextCapacityCable, 0)
                solCplmt.lossesInStat[currentStation, scen] = solCplmt.powerReceived[currentStation, scen] - solCplmt.powerInStat[currentStation, scen]
                solCplmt.lossesInStatCable[currentStation, scen] = max(solCplmt.powerInStat[currentStation, scen] - currentCapacityCable, 0)
    if diff > 0:
        for t in turbinesToChange:
            currentStation = np.argmax(initSol.z[t, :])
            initSol.z[t, currentStation] = 0
            initSol.z[t, randS] = 1
        return True, initSol
    else:
        initSol.x[randS, randStatType] = 0
        initSol.yonoff[randS, randCableType] = 0
        solCplmt = solCplmtCopy
    return False, initSol

def getNeighbor2(instance, initSol, solCplmt):
    # Neighbor : close station
    openStationsIndexes = [s for s in range(len(instance.stations)) if solCplmt.openStations[s] == 1]
    if (len(openStationsIndexes) == 1):
        return False, initSol
    randS = np.random.choice(openStationsIndexes)
    if solCplmt.openStations[randS] == 0:
        print("Not OK")
        return
    
    newSol = deepcopy(initSol)
    newSolCplmt = deepcopy(solCplmt)

    solCplmt.openStations[randS] = 0
    randCableType = np.argmax(newSol.y_off_on[randS, :])
    randStatType = np.argmax(newSol.x[randS, :])
    newSol.x[randS, randStatType] = 0
    newSol.y_off_on[randS, randCableType] = 0
    diff = instance.substation_types[randStatType].cost
    print(diff)

    turbinesToChange = []
    for t in range(len(instance.turbines)):
        if newSol.z[t, randS] == 1 :
            turbinesToChange.append(t)
            bestS = np.argmax(solCplmt.openStations)
            bestDist = instance.stations[bestS].distance(instance.turbines[t])
            for s in range(len(instance.stations)) :
                if solCplmt.openStations[s] == 0: 
                    continue
                dist = instance.stations[s].distance(instance.turbines[t])
                if dist < bestDist :
                    dist = bestDist
                    bestS = s
            newSol.z[t, s] = 1
            newSol.z[t, randS] = 0
            stationType = np.argmax(initSol.x[bestS, :]) if np.any(initSol.x[bestS, :] == 1) else -1
            cableType = np.argmax(initSol.y_off_on[bestS, :]) if np.any(initSol.y_off_on[bestS, :] == 1) else -1
            capacityStat = instance.substation_types[stationType].rating
            capacityCable = instance.land_to_sub_cables[cableType].rating
            for scen in range(len(instance.scenarios)):
                newSolCplmt.powerReceived[bestS, scen] += instance.scenarios[scen].power_generation
                newSolCplmt.powerInStat[bestS, scen] = min(solCplmt.powerReceived[bestS, scen], capacityStat)
                newSolCplmt.lossesInStat[bestS, scen] = solCplmt.powerReceived[bestS, scen] - solCplmt.powerInStat[bestS, scen]
                newSolCplmt.lossesInStatCable[bestS, scen] = max(solCplmt.powerInStat[bestS, scen] - capacityCable, 0)
            diff += instance.curtailing_cost * (solCplmt.lossesInStat[bestS, :].sum() + solCplmt.lossesInStatCable[bestS].sum() - newSolCplmt.lossesInStat[bestS, :].sum() - newSolCplmt.lossesInStatCable[bestS].sum())

    if diff > 0:
        solCplmt = newSolCplmt
        return True, newSol
    else:
        return False, initSol

def getNeighbor1(instance, initSol, solCplmt):
    # Neighbor : changer type de station
    openStationsIndexes = [s for s in range(len(instance.stations)) if solCplmt.openStations[s] == 1]
    randS = np.random.choice(openStationsIndexes)
    randCableType = np.argmax(initSol.y_off_on[randS, :])
    randSType = np.argmax(initSol.x[randS, :])
    newSType = rd.randint(0, len(instance.substation_types) - 1)
    newcapacityStat = instance.substation_types[newSType].rating
    capacityCable = instance.land_to_sub_cables[randCableType].rating
    diff = instance.substation_types[randSType].cost - instance.substation_types[newSType].cost
    
    diffLoss = 0

    for scen in range(len(instance.scenarios)):
        newPowerInStat = min(solCplmt.powerReceived[randS, scen], newcapacityStat)
        diffLoss += solCplmt.lossesInStat[randS, scen] - (solCplmt.powerReceived[randS, scen] - solCplmt.powerInStat[randS, scen])
        diffLoss += solCplmt.lossesInStatCable[randS, scen] - max(newPowerInStat - capacityCable, 0)
    
    diff += instance.curtailing_cost * diffLoss
    
    if diff > 0:
        initSol.x[randS, newSType] = 1
        initSol.x[randS, randSType] = 0
        for scen in range(len(instance.scenarios)):
            solCplmt.powerInStat[randS, scen] = min(solCplmt.powerReceived[randS, scen], newcapacityStat)
            solCplmt.lossesInStat[randS, scen] = solCplmt.powerReceived[randS, scen] - solCplmt.powerInStat[randS, scen]
            solCplmt.lossesInStatCable[randS, scen] = max(solCplmt.powerInStat[randS, scen] - capacityCable, 0)
        print("We found a good neighbor 1")
        return True, initSol
    else : 
        return False, initSol

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
        initSol.export_solution_json("small_Try.json")
        solCplmt = SolutionComplement(instance, initSol)
        nbIters = -1
        voisType = 0
        nbIterWOSucc = 0
        while nbIters < nbMaxIters :
            nbIters += 1
            success, initSol = getNeighbor(instance, initSol, solCplmt, voisType)
            if (success) :
                nbIterWOSucc = 0
            else :
                nbIterWOSucc += 1
    
            if nbIterWOSucc >= 10 :
                voisType += 1
                print("Upgrading to voisinage ", voisType)
                if voisType == 2:
                    break
                nbIterWOSucc = 0
        initSol.export_solution_json("small_Try_Fin.json")

def mainLS():
    return mainLSinst(Instance("./instances/small.json"))

mainLS()
