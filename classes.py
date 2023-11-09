import json
from typing import List
import numpy as np
from logzero import logger


class Cable:
    id: int
    rating: float
    probability_of_failure: float
    variable_cost: float
    fixed_cost: float

    def __init__(self, args) -> None:
        self.id = args["id"]
        self.rating = args["rating"]
        if "probability_of_failure" in args.keys():
            self.probability_of_failure = args["probability_of_failure"]
        else:
            self.probability_of_failure = None
        self.variable_cost = args["variable_cost"]
        self.fixed_cost = args["fixed_cost"]

        return None


class LandToSubstationCable(Cable):
    def __init__(self, args) -> None:
        super().__init__(args)


class SubstationToSubstationCable(Cable):
    def __init__(self, args) -> None:
        super().__init__(args)


######### TURBINES


class CoordinatePoint:
    id: int
    x: float
    y: float

    def __init__(self, dict) -> None:
        self.id = dict["id"]
        self.x = dict["x"]
        self.y = dict["y"]

        return None

    def distance(self, other):
        assert isinstance(other, CoordinatePoint)
        return np.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


class Turbine(CoordinatePoint):
    def __init__(self, dict) -> None:
        super().__init__(dict)


######### SCENARIOS


class Scenario:
    id: int
    power_generation: float
    probability: float

    def __init__(self, dict) -> None:
        self.id = dict["id"]
        self.power_generation = dict["power_generation"]
        self.probability = dict["probability"]

        return None


########## STATIONS


class Station(CoordinatePoint):
    def __init__(self, dict) -> None:
        super().__init__(dict)


class LandStation(Station):
    def __init__(self) -> None:
        args = {"id": 0, "x": 0, "y": 0}
        super().__init__(args)


class SubstationType:
    cost: float
    rating: float
    probability_of_failure: float
    id: int

    def __init__(self, dict) -> None:
        self.cost = dict["cost"]
        self.rating = dict["rating"]
        self.probability_of_failure = dict["probability_of_failure"]
        self.id = dict["id"]

        return None


class Substation(Station):
    substation_type: SubstationType

    def __init__(self, dict, substation_type) -> None:
        super().__init__(dict)
        self.substation_type = substation_type

        return None


class Instance:
    stations: List[Station]
    turbines: List[Turbine]
    land_to_sub_cables: List[LandToSubstationCable]
    sub_sub_cable_types: List[SubstationToSubstationCable]
    scenarios: List[Scenario]
    substation_types: List[SubstationType]

    fixed_cost_cable: float
    variable_cost_cables: float
    curtailing_penalty: float
    curtailing_cost: float
    maximum_power: float
    maximum_curtailing: float

    def __init__(self, filepath) -> None:
        with open(filepath, "r") as f:
            data = json.load(f)

        # Land substation cable types
        self.land_to_sub_cables = []
        land_substation_cable_types = data["land_substation_cable_types"]
        for land_substation_cable_type in land_substation_cable_types:
            new_cable = LandToSubstationCable(land_substation_cable_type)
            self.land_to_sub_cables.append(new_cable)

        # Substation to sub cable types
        self.sub_to_sub_cables = []
        sub_sub_cable_types = data["substation_substation_cable_types"]
        for sub_sub_cable_type in sub_sub_cable_types:
            new_cable = SubstationToSubstationCable(sub_sub_cable_type)
            self.sub_to_sub_cables.append(new_cable)

        # Turbines
        self.turbines = []
        turbines = data["wind_turbines"]
        for turbine in turbines:
            new_turbine = Turbine(turbine)
            self.turbines.append(new_turbine)

        # Wind scenarios
        self.scenarios = []
        scenarios = data["wind_scenarios"]
        for scenario in scenarios:
            new_scenario = Scenario(scenario)
            self.scenarios.append(new_scenario)

        # Stations
        self.stations = []
        stations = data["substation_locations"]
        for station in stations:
            new_station = Station(station)
            self.stations.append(new_station)

        # Substation types
        self.substation_types = []
        substation_types = data["substation_types"]
        for substation_type in substation_types:
            new_substation_type = SubstationType(substation_type)
            self.substation_types.append(new_substation_type)

        general_params = data["general_parameters"]

        self.fixed_cost_cable = general_params["fixed_cost_cable"]
        self.variable_cost_cables = general_params["variable_cost_cable"]
        self.curtailing_penalty = general_params["curtailing_penalty"]
        self.curtailing_cost = general_params["curtailing_cost"]
        self.maximum_power = general_params["maximum_power"]
        self.maximum_curtailing = general_params["maximum_curtailing"]

        return None

    def get_nb_turbines(self):
        return len(self.turbines)


class Solution:
    instance: Instance

    # Shape (nb_positions_substations, nb_substation_types)
    x: np.ndarray

    # Cables offshore to onshore: shape (nb_substations, nb_cable_types)
    y_off_on: np.ndarray

    # Cables offshore to offshore: shape (nb_substations, nb_substations, nb_types_cables_sub_to_sub)
    y_off_off: np.ndarray

    # shape (nb_turbines, nb_substations)
    z: np.ndarray

    def __init__(self, instance, x, y_off_on, y_off_off, z) -> None:
        self.instance = instance
        self.x = x
        self.y_off_on = y_off_on
        self.y_off_off = y_off_off
        self.z = z

        return None

    def export_solution_json(self, filepath):
        # TODO
        # Substations open
        # substation_substation_cables
        # turbines

        result = {"substations": [], "substation_substation_cables": [], "turbines": []}

        for i, line in enumerate(self.x):
            local = {}
            if not np.any(line == 1):
                continue
            id_type = int(np.argmax(line))
            local["id"] = i + 1
            local["substation_type"] = id_type + 1

            cable_type_id = int(np.argmax(self.y_off_on[i]))
            local["land_cable_type"] = cable_type_id + 1

            result["substations"].append(local)

        # Substation to substation cables

        for i, line in enumerate(self.y_off_off):
            local = {}
            sub_sub_cable_type = -1
            for j in range(i, self.y_off_off.shape[1]):
                if not np.any(self.y_off_off[i, j, :] == 1):
                    continue
                sub_sub_cable_type = int(np.argmax(self.y_off_off[i, j, :]) + 1)
            if sub_sub_cable_type == -1 :
                continue
            local["substation_id"] = i + 1
            local["other_substation_id"] = j + 1
            local["cable_type"] = sub_sub_cable_type

            result["substation_substation_cables"].append(local)

        # Turbines
        for i, line in enumerate(self.z):
            local = {}
            if not np.any(line == 1):
                continue
            id_sub = int(np.argmax(self.z[i]) + 1)
            local["id"] = i + 1
            local["substation_id"] = id_sub
            result["turbines"].append(local)

        with open(filepath, "w") as f:
            print(result)
            json.dump(result, f)

        logger.info("Results exported to JSON.")

        #  open_stations_types = np.argmax(self.x[np.any(self.x == 1, axis=1)], axis=1)

        return None
