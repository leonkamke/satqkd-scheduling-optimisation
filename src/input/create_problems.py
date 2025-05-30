from datetime import datetime
import os
from pathlib import Path
import random
import json
import uuid
import numpy as np
import calendar
from .data_generation import get_satellite_passes
from gurobipy import *
from ..utils import *
import sys


# Locations for ground terminals in europe
europe_ground_terminals = {
    0: {"lat": 51.5074, "lon": -0.1278, "alt": 35},  # London, England
    1: {"lat": 48.8566, "lon": 2.3522, "alt": 35},  # Paris, France
    2: {"lat": 52.5200, "lon": 13.4050, "alt": 34},  # Berlin, Germany
    3: {"lat": 41.9028, "lon": 12.4964, "alt": 21},  # Rome, Italy
    4: {"lat": 40.4168, "lon": -3.7038, "alt": 667},  # Madrid, Spain
    5: {"lat": 50.0755, "lon": 14.4378, "alt": 200},  # Prague, Czech Republic
    6: {"lat": 47.4979, "lon": 19.0402, "alt": 96},  # Budapest, Hungary
    7: {"lat": 59.3293, "lon": 18.0686, "alt": 28},  # Stockholm, Sweden
    8: {"lat": 60.1695, "lon": 24.9354, "alt": 16},  # Helsinki, Finland
    9: {"lat": 55.6761, "lon": 12.5683, "alt": 1},  # Copenhagen, Denmark
    10: {"lat": 54.6872, "lon": 25.2797, "alt": 112},  # Vilnius, Lithuania
    11: {"lat": 56.9496, "lon": 24.1052, "alt": 6},  # Riga, Latvia
    12: {"lat": 53.9006, "lon": 27.5590, "alt": 220},  # Minsk, Belarus
    13: {"lat": 50.8503, "lon": 4.3517, "alt": 13},  # Brussels, Belgium
    14: {"lat": 48.2082, "lon": 16.3738, "alt": 193},  # Vienna, Austria
    15: {"lat": 46.2044, "lon": 6.1432, "alt": 375},  # Geneva, Switzerland
    16: {"lat": 42.6977, "lon": 23.3219, "alt": 550},  # Sofia, Bulgaria
    17: {"lat": 44.4268, "lon": 26.1025, "alt": 70},  # Bucharest, Romania
    18: {"lat": 45.8150, "lon": 15.9819, "alt": 122},  # Zagreb, Croatia
    19: {"lat": 43.8563, "lon": 18.4131, "alt": 500,},  # Sarajevo, Bosnia and Herzegovina
    20: {"lat": 42.4410, "lon": 19.2621, "alt": 107},  # Podgorica, Montenegro
    21: {"lat": 41.9981, "lon": 21.4254, "alt": 240},  # Skopje, North Macedonia
    22: {"lat": 39.9208, "lon": 32.8541, "alt": 938},  # Ankara, Turkey
    23: {"lat": 37.9838, "lon": 23.7275, "alt": 70},  # Athens, Greece
    24: {"lat": 45.4642, "lon": 9.1900, "alt": 120},  # Milan, Italy
    25: {"lat": 44.8381, "lon": -0.5792, "alt": 7},  # Bordeaux, France
    26: {"lat": 41.3851, "lon": 2.1734, "alt": 12},  # Barcelona, Spain
    27: {"lat": 43.7102, "lon": 7.2620, "alt": 10},  # Nice, France
    28: {"lat": 49.6117, "lon": 6.1319, "alt": 289},  # Luxembourg City, Luxembourg
    29: {"lat": 51.2093, "lon": 3.2247, "alt": 8},  # Bruges, Belgium
    30: {"lat": 53.3498, "lon": -6.2603, "alt": 20},  # Dublin, Ireland
    31: {"lat": 55.9533, "lon": -3.1883, "alt": 47},  # Edinburgh, Scotland
    32: {"lat": 54.9783, "lon": -1.6174, "alt": 46},  # Newcastle, England
    33: {"lat": 55.8642, "lon": -4.2518, "alt": 20},  # Glasgow, Scotland
    34: {"lat": 47.3769, "lon": 8.5417, "alt": 408},  # Zurich, Switzerland
    35: {"lat": 47.0707, "lon": 15.4395, "alt": 353},  # Graz, Austria
    36: {"lat": 49.4521, "lon": 11.0767, "alt": 309},  # Nuremberg, Germany
    37: {"lat": 50.1109, "lon": 8.6821, "alt": 112},  # Frankfurt, Germany
    38: {"lat": 45.7607, "lon": 4.8357, "alt": 173},  # Lyon, France
    39: {"lat": 44.4949, "lon": 11.3426, "alt": 54},  # Bologna, Italy
    40: {"lat": 40.8518, "lon": 14.2681, "alt": 17},  # Naples, Italy
    41: {"lat": 43.6047, "lon": 1.4442, "alt": 146},  # Toulouse, France
    42: {"lat": 51.2194, "lon": 4.4025, "alt": 8},  # Antwerp, Belgium
    43: {"lat": 51.5072, "lon": 0.1276, "alt": 10},  # Brighton, England
    44: {"lat": 57.7089, "lon": 11.9746, "alt": 12},  # Gothenburg, Sweden
    45: {"lat": 60.3932, "lon": 5.3242, "alt": 20},  # Bergen, Norway
    46: {"lat": 59.9139, "lon": 10.7522, "alt": 23},  # Oslo, Norway
    47: {"lat": 63.4305, "lon": 10.3951, "alt": 10},  # Trondheim, Norway
    48: {"lat": 59.8586, "lon": 17.6389, "alt": 15},  # Uppsala, Sweden
    49: {"lat": 55.4038, "lon": 10.4024, "alt": 5},  # Odense, Denmark
    50: {"lat": 54.3520, "lon": 18.6466, "alt": 7},  # Gdansk, Poland
    51: {"lat": 52.2297, "lon": 21.0122, "alt": 113},  # Warsaw, Poland
    52: {"lat": 50.0647, "lon": 19.9450, "alt": 219},  # Krakow, Poland
    53: {"lat": 52.4064, "lon": 16.9252, "alt": 60},  # Poznan, Poland
    54: {"lat": 53.0138, "lon": 18.5984, "alt": 67},  # Torun, Poland
    55: {"lat": 52.5204, "lon": 4.8952, "alt": 2},  # Amsterdam, Netherlands
    56: {"lat": 51.9244, "lon": 4.4777, "alt": 0},  # Rotterdam, Netherlands
    57: {"lat": 50.8514, "lon": 5.6909, "alt": 45},  # Maastricht, Netherlands
    58: {"lat": 51.2277, "lon": 6.7735, "alt": 45},  # Dusseldorf, Germany
    59: {"lat": 51.5136, "lon": 7.4653, "alt": 60},  # Dortmund, Germany
    60: {"lat": 53.5511, "lon": 9.9937, "alt": 6},  # Hamburg, Germany
    61: {"lat": 53.0758, "lon": 8.8072, "alt": 12},  # Bremen, Germany
    62: {"lat": 48.1351, "lon": 11.5820, "alt": 519},  # Munich, Germany
    63: {"lat": 47.5677, "lon": 7.5970, "alt": 244},  # Basel, Switzerland
    64: {"lat": 45.1885, "lon": 5.7245, "alt": 212},  # Grenoble, France
    65: {"lat": 43.2965, "lon": 5.3698, "alt": 10},  # Marseille, France
    66: {"lat": 44.8378, "lon": 20.4216, "alt": 117},  # Belgrade, Serbia
    67: {"lat": 42.8794, "lon": 20.8756, "alt": 609},  # Prizren, Kosovo
    68: {"lat": 41.3275, "lon": 19.8189, "alt": 110},  # Tirana, Albania
    69: {"lat": 42.5624, "lon": 1.5333, "alt": 1023},  # Andorra la Vella, Andorra
    70: {"lat": 46.0569, "lon": 14.5058, "alt": 298},  # Ljubljana, Slovenia
    71: {"lat": 47.5008, "lon": 19.0567, "alt": 104},  # Debrecen, Hungary
    72: {"lat": 50.0750, "lon": 19.9030, "alt": 281},  # Katowice, Poland
    73: {"lat": 46.7667, "lon": 23.5833, "alt": 360},  # Cluj-Napoca, Romania
    74: {"lat": 45.6486, "lon": 25.6062, "alt": 600},  # Brasov, Romania
    75: {"lat": 40.1786, "lon": 44.5126, "alt": 989},  # Yerevan, Armenia
    76: {"lat": 38.0194, "lon": 23.8439, "alt": 125},  # Kifisia, Greece
    77: {"lat": 36.7213, "lon": -4.4214, "alt": 11},  # Malaga, Spain
    78: {"lat": 37.9922, "lon": -1.1307, "alt": 43},  # Murcia, Spain
    79: {"lat": 43.2627, "lon": -2.9253, "alt": 19},  # Bilbao, Spain
    80: {"lat": 39.4699, "lon": -0.3763, "alt": 15},  # Valencia, Spain
    81: {"lat": 38.7169, "lon": -9.1390, "alt": 100},  # Lisbon, Portugal
    82: {"lat": 41.1496, "lon": -8.6109, "alt": 104},  # Porto, Portugal
    83: {"lat": 38.7369, "lon": -9.1390, "alt": 12},  # Faro, Portugal
    84: {"lat": 62.2426, "lon": 25.7473, "alt": 117},  # Jyvaskyla, Finland
    85: {"lat": 58.3806, "lon": 26.7251, "alt": 57},  # Tartu, Estonia
    86: {"lat": 56.3322, "lon": 43.9978, "alt": 171},  # Nizhny Novgorod, Russia
    87: {"lat": 55.7558, "lon": 37.6173, "alt": 156},  # Moscow, Russia
    88: {"lat": 59.9343, "lon": 30.3351, "alt": 20},  # Saint Petersburg, Russia
    89: {"lat": 53.1959, "lon": 50.1007, "alt": 160},  # Samara, Russia
    90: {"lat": 48.2920, "lon": 25.9358, "alt": 248},  # Chernivtsi, Ukraine
    91: {"lat": 46.4825, "lon": 30.7233, "alt": 50},  # Odessa, Ukraine
    92: {"lat": 50.4017, "lon": 30.2525, "alt": 179},  # Kyiv, Ukraine
    93: {"lat": 49.5535, "lon": 25.5948, "alt": 320},  # Ternopil, Ukraine
    94: {"lat": 45.2631, "lon": 19.8310, "alt": 82},  # Novi Sad, Serbia
    95: {"lat": 41.7208, "lon": 44.7831, "alt": 450},  # Tbilisi, Georgia
    96: {"lat": 38.2484, "lon": 21.7346, "alt": 15},  # Patras, Greece
    97: {"lat": 57.1424, "lon": -2.0927, "alt": 65},  # Aberdeen, Scotland
    98: {"lat": 60.4720, "lon": 8.4689, "alt": 140},  # Drammen, Norway
    99: {"lat": 51.2195, "lon": 22.5684, "alt": 174},  # Lublin, Poland
}


class ServiceTarget:
    def __init__(self, id, applicationId, priority, nodeId, requestedOperation):
        self.id = id
        self.applicationId = applicationId
        self.priority = priority
        self.nodeId = nodeId
        self.requestedOperation = requestedOperation

    def __repr__(self):
        return (
            f"ServiceTarget(id={self.id}, applicationId={self.applicationId}, nodeId={self.nodeId}, "
            f"priority={self.priority}, requestedOperation={self.requestedOperation})"
        )

    def to_dict(self):
        return self.__dict__


def get_service_targets(number_ground_terminals, number_application_contexts_per_node):
    service_targets_dict_list = []
    serviceTargetId = 0
    applicationId = 0
    for id in range(number_ground_terminals):
        for _ in range(number_application_contexts_per_node):
            priority1 = round(random.uniform(0.01, 1.0), 2)

            requestedOperation = "QKD"
            service_targets_dict_list.append(
                ServiceTarget(
                    serviceTargetId, applicationId, priority1, id, requestedOperation
                ).to_dict()
            )
            serviceTargetId += 1

            priority2 = round(random.uniform(0.01, 1.0), 2)
            requestedOperation = "OPTICAL_ONLY"
            service_targets_dict_list.append(
                ServiceTarget(
                    serviceTargetId, applicationId, priority2, id, requestedOperation
                ).to_dict()
            )
            serviceTargetId += 1

            applicationId += 1

    return service_targets_dict_list


def save_problem_instances_to_json(problem_instances, file_name):
    with open(file_name, "w") as f:
        json.dump(problem_instances, f, indent=4, default=str)


def generate_problem_instance(
    coverage_start,
    coverage_end,
    ground_terminals,
    step_duration=10,
    min_elevation_angle=15,
    number_app_contexts_per_node=10,
):
    # Calculate satellite passes over ground terminals for QUARC mission
    satellite_passes_dict_list = get_quarc_satellite_passes(
        ground_terminals,
        coverage_start,
        coverage_end,
        step_duration,
        min_elevation_angle,
    )

    # Calculate service targets
    service_targets_dict_list = get_service_targets(
        len(ground_terminals), number_app_contexts_per_node
    )

    return {
        "problem_instance_id": str(uuid.uuid4()),
        "coverage_start": str(coverage_start),
        "coverage_end": str(coverage_end),
        "min_elevation_angle": min_elevation_angle,
        "step_duration": step_duration,
        "number_ground_terminals": len(ground_terminals),
        "number_application_contexts_per_node": number_app_contexts_per_node,
        "number_satellite_passes": len(satellite_passes_dict_list),
        "number_service_targets": len(service_targets_dict_list),
        "satellite_passes": satellite_passes_dict_list,
        "service_targets": service_targets_dict_list,
    }
    

# skip the script name
args = sys.argv[1:]
params = {}
for i in range(0, len(args), 2):
    if args[i].startswith("-") and (i + 1) < len(args):
        key = args[i].lstrip("-")
        val = args[i + 1]
        params[key] = val

min_elevation_angle = 15
step_duration = 10
locations = "Europe"
number_app_contexts_per_node = int(params["num_app_contexts"])
planning_horizon = int(params["planning_horizon"])
coverage_duration = np.timedelta64(planning_horizon, "h")
ground_terminals = europe_ground_terminals
name = (
    "Dataset_year_"
    + params["ground_terminal"]
    + "_"
    + str(planning_horizon)
    + "h_"
    + str(number_app_contexts_per_node)
    + "app"
)


output_base = "./src/input/data/" + name + "/"
for month in range(1, 13):
    for type, day in [("train", 5), ("train", 25), ("test", 15)]:
        try:
            date = np.datetime64(f"2024-{month:02d}-{day:02d}T00:00:00")
            coverage_start = date
            coverage_end = coverage_start + coverage_duration

            filename_json = (
                output_base
                + f"{type}_{locations}_{str(planning_horizon)}h_{str(number_app_contexts_per_node)}app_{calendar.month_abbr[month].lower()}_{day}.json"
            )
            filename_mps = (
                output_base
                + f"{type}_{locations}_{str(planning_horizon)}h_{str(number_app_contexts_per_node)}app_{calendar.month_abbr[month].lower()}_{day}.mps"
            )
            if not os.path.exists(filename_json):
                print(coverage_start)
                print(coverage_end)
                print(planning_horizon)
                print(filename_json)

                problem_instances = [
                    generate_problem_instance(
                        coverage_start,
                        coverage_end,
                        ground_terminals,
                        step_duration,
                        min_elevation_angle,
                        number_app_contexts_per_node,
                    )
                ]

                os.makedirs(output_base, exist_ok=True)
                save_problem_instances_to_json(problem_instances, str(filename_json))
                print(f"Saved: {filename_json}")

            if True:  # not os.path.exists(filename_mps):
                # Read problem instance
                problemInstance = read_problem_instance(filename_json)
                satellitePasses = problemInstance["satellite_passes"]
                serviceTargets = problemInstance["service_targets"]

                V = list(range(len(satellitePasses)))
                S = list(range(len(serviceTargets)))

                di, ti, bi, ni, fi, oi = {}, {}, {}, {}, {}, {}
                reference_time = datetime.fromisoformat(
                    problemInstance["coverage_start"]
                )

                for idx, sp in enumerate(satellitePasses):
                    start_time = datetime.fromisoformat(sp["startTime"])
                    end_time = datetime.fromisoformat(sp["endTime"])
                    ti[idx] = (start_time - reference_time).total_seconds()
                    di[idx] = (end_time - start_time).total_seconds()
                    bi[idx] = sp["achievableKeyVolume"]
                    oi[idx] = 1 if sp["achievableKeyVolume"] == 0.0 else 0
                    ni[idx] = sp["nodeId"]
                    fi[idx] = sp["orbitId"]

                pj, sj, mj, aj = {}, {}, {}, {}
                for idx, st in enumerate(serviceTargets):
                    pj[idx] = st["priority"]
                    sj[idx] = st["nodeId"]
                    mj[idx] = 1 if st["requestedOperation"] == "QKD" else 0
                    aj[idx] = st["applicationId"]

                T_min = 60  # Minimum time between consecutive contacts in seconds

                model = Model("Satellite Optimization")

                # Decision variables: only create if node and mode match
                x = {}
                for i in V:
                    for j in S:
                        if ni[i] == sj[j] and not (oi[i] == 1 and mj[j] == 1):
                            x[i, j] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")

                model.update()

                # Objective
                model.setObjective(
                    quicksum(x[i, j] * pj[j] * (1 + bi[i] * mj[j]) for (i, j) in x),
                    GRB.MAXIMIZE,
                )

                # Constraints: each pass at most once
                for i in V:
                    model.addConstr(quicksum(x[i, j] for j in S if (i, j) in x) <= 1)

                # Constraints: each target at most once
                for j in S:
                    model.addConstr(quicksum(x[i, j] for i in V if (i, j) in x) <= 1)

                # Non-overlapping satellite passes (optimized)
                sorted_V = sorted(V, key=lambda i: ti[i])
                for idx1, i1 in enumerate(sorted_V):
                    for idx2 in range(idx1 + 1, len(sorted_V)):
                        i2 = sorted_V[idx2]
                        if ti[i2] - (ti[i1] + di[i1]) >= T_min:
                            break
                        expr1 = quicksum(x[i1, k] for k in S if (i1, k) in x)
                        expr2 = quicksum(x[i2, k] for k in S if (i2, k) in x)
                        # Use big-M constraint
                        M = 99999
                        model.addConstr(
                            (ti[i1] + di[i1] + T_min)
                            <= (ti[i2] + (2 - expr1 - expr2) * M)
                        )

                # Save the model to MPS file
                model.write(filename_mps)
                print(f"Saved: {filename_mps}")
        except Exception as e:
            print(f"Failed for file " + filename_json + " with exception: " + str(e))
