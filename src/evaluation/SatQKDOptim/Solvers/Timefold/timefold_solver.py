import sys
from pathlib import Path
from datetime import datetime
import json
import subprocess
import os
import uuid
import time
import traceback


def read_contacts_from_timefold(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)

    contacts = []
    for contact in data:
        service_target = contact.get("serviceTarget", {})
        satellite_pass = contact.get("satellitePass", {})

        contacts.append(
            {
                "serviceTarget": {
                    "id": service_target.get("id"),
                    "applicationId": service_target.get("applicationId"),
                    "priority": service_target.get("priority"),
                    "requestedOperation": service_target.get("requestedOperation"),
                    "nodeId": service_target.get("nodeId"),
                },
                "satellitePass": {
                    "id": satellite_pass.get("id"),
                    "nodeId": satellite_pass.get("nodeId"),
                    "startTime": (
                        datetime(*satellite_pass.get("startTime")).isoformat()
                        if satellite_pass.get("startTime")
                        else None
                    ),
                    "endTime": (
                        datetime(*satellite_pass.get("endTime")).isoformat()
                        if satellite_pass.get("endTime")
                        else None
                    ),
                    "achievableKeyVolume": satellite_pass.get("achievableKeyVolume"),
                    "orbitId": satellite_pass.get("orbitId"),
                },
            }
        )

    return contacts


def parse_args_to_dict(argv):
    args_dict = {}
    i = 1  # skip java timefold.jar
    while i < len(argv):
        if argv[i].startswith("-"):
            key = argv[i].lstrip("-")
            # Make sure there's a value after the key
            if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
                args_dict[key] = argv[i + 1]
                i += 2
            else:  # Else skip
                i += 1
        else:  # Else skip
            i += 1
    return args_dict


# Helper function
def read_problem_instance(instance_path):
    with open(instance_path, "r") as file:
        data = json.load(file)
        return data[0]


# Helper function
def calculate_objective_function(contacts):
    result = 0
    for contact in contacts:
        satellite_pass = contact["satellitePass"]
        service_target = contact["serviceTarget"]

        priority = service_target["priority"]
        achievable_key_volume = satellite_pass["achievableKeyVolume"]
        operation_mode = 1 if service_target["requestedOperation"] == "QKD" else 0
        result += priority * (1 + achievable_key_volume * operation_mode)
    return result


jar_result = None
params = []
args = None
try:
    # Read the arguments
    args = parse_args_to_dict(sys.argv)

    # Extract and delete data that needs specific formatting
    instance_path = Path(args["inst"])
    seed = args["seed"]
    del args["inst"]
    del args["seed"]

    config = args

    for k, v in config.items():
        params += ["-" + k, str(v)]

    if len(params) == 0:
        params = [
            "-constructionHeuristicType",
            "NONE",
            "-ls1Type",
            "NONE",
            "-ls2Type",
            "NONE",
        ]

    # Read user home from file
    user_home = None
    with open("./Solvers/Timefold/cluster_home.txt", "r") as f:
        user_home = f.read().strip()

    # Set max_solve_time
    max_solve_time = None
    with open("./Solvers/Timefold/max_solve_time.txt", "r") as file:
        max_solve_time = int(file.read().strip())

    # Compile and build Java Timefold project
    # Remove for big experiments (takes some time)
    """mvn_build_command = [
        os.path.join(user_home, "maven/apache-maven-3.9.9/bin/mvn"),
        "clean",
        "package"
    ]
    subprocess.run(mvn_build_command, cwd="./Solvers/Timefold/timefold_solver")"""

    # Run Timefold jar file
    java_path = os.path.join(
        user_home, "java/openlogic-openjdk-17.0.14+7-linux-x64/bin/java"
    )
    tmp_file_name = str(uuid.uuid4())
    java_command = [
        java_path,
        "-Xmx4g",
        "-jar",
        "./Solvers/Timefold/timefold_solver/target/timefold_solver-1.0-SNAPSHOT-jar-with-dependencies.jar",
        "-inst",
        instance_path,
        "-seed",
        str(seed),
        "-uuid",
        tmp_file_name,
    ]
    start_time = time.time()
    jar_result = subprocess.run(java_command + params, capture_output=True, text=True)
    end_time = time.time()

    contacts_file_path = "./Tmp/" + tmp_file_name + ".json"
    contacts = read_contacts_from_timefold(contacts_file_path)
    os.remove(contacts_file_path)

    quality = 0
    if len(contacts) > 0:
        quality = int(calculate_objective_function(contacts))
    solve_time = round(end_time - start_time, 4)

    result = {
        "status": "SUCCESS",
        "par10": max_solve_time * 10,
        "quality": 1 if quality <= 0 else quality,
        "solve_time": solve_time,
        "solver_call": None,
    }
    print("Timefold solver output is:")
    print(result)

except Exception as ex:
    print(ex)
    exception_file_name = "./Tmp/" + str(uuid.uuid4()) + ".txt"
    with open(exception_file_name, "w") as file:
        file.write("Optimization method failed with exception:\n")
        file.write(str(ex) + "\n")
        file.write(traceback.format_exc() + "\n")
        file.write("Java output: " + jar_result.stdout + "\n")
        file.write("Java output: " + jar_result.stderr + "\n")
        file.write("This was the configuration:\n")
        file.write(str(config))
        file.write("Sys args: " + str(sys.argv))
