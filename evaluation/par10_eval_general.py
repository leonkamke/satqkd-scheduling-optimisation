import os
import time
import subprocess

### Gurobi

europe_par10_eval_gurobi_100000s_900s = [
    "sparkle initialise",
    "sparkle add_instances ../../SatQKDOptim/Instances/Dataset_Europe_Hard_Train",
    "sparkle add_instances ../../SatQKDOptim/Instances/Dataset_Europe_Hard_Test",
    "sparkle add_solver ../../SatQKDOptim/Solvers/Gurobi",
    "sed -i '1s/.*/900/' ./Solvers/Gurobi/max_solve_time.txt",
    "rm -rf ./Settings && cp -r ../../Settings .",
    "sed -i '2s/.*/objectives = par10/' ./Settings/sparkle_settings.ini",
    "sed -i '13s/.*/wallclock_time = 79200/' ./Settings/sparkle_settings.ini",
    "sed -i '31s/.*/time = 23:30:00/' ./Settings/sparkle_settings.ini",
    "sparkle configure_solver --solver Solvers/Gurobi --instance-set-train Instances/Dataset_Europe_Hard_Train --instance-set-test Instances/Dataset_Europe_Hard_Test --target-cutoff-time 930 --objectives par10",
]

### SCIP

europe_par10_eval_scip_100000s_900s = [
    "sparkle initialise",
    "sparkle add_instances ../../SatQKDOptim/Instances/Dataset_Europe_General_Train",
    "sparkle add_instances ../../SatQKDOptim/Instances/Dataset_Europe_General_Test",
    "sparkle add_solver ../../SatQKDOptim/Solvers/SCIP",
    "sed -i '1s/.*/900/' ./Solvers/SCIP/max_solve_time.txt",
    "rm -rf ./Settings && cp -r ../../Settings .",
    "sed -i '2s/.*/objectives = par10/' ./Settings/sparkle_settings.ini",
    "sed -i '13s/.*/wallclock_time = 79200/' ./Settings/sparkle_settings.ini",
    "sed -i '31s/.*/time = 23:30:00/' ./Settings/sparkle_settings.ini",
    "sparkle configure_solver --solver Solvers/SCIP --instance-set-train Instances/Dataset_Europe_General_Train --instance-set-test Instances/Dataset_Europe_General_Test --target-cutoff-time 930 --objectives par10",
]


# List of evaluations
evaluations = [
      {
         "name": "europe_par10_eval_gurobi_100000s_900s",
         "commands": europe_par10_eval_gurobi_100000s_900s,
      },
    {
        "name": "europe_par10_eval_scip_100000s_900s",
        "commands": europe_par10_eval_scip_100000s_900s,
    }
]

BASE_DIR = os.getcwd()


def wait_until_no_jobs():
    print("\nWaiting for all jobs to finish...")
    while True:
        # Execute squeue --me command
        result = subprocess.run(["squeue", "--me"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")

        # If only header is present, there are no jobs (except for evaluation job itself)
        if len(lines) <= 2:
            print("All jobs completed.\n")
            return
        else:
            print(f"{len(lines)-2} job(s) still running...")
            time.sleep(300)  # Wait five minutes before checking again


def run_evaluation(eval):
    # Go into results folder
    os.chdir("par10_eval_hard")

    # Create new folder for evaluation (with timestamp)
    folder_name = f"{eval['name']}"
    os.makedirs(folder_name, exist_ok=False)
    os.chdir(folder_name)

    print(f"############# Running {eval['name']} in {os.getcwd()} #############")

    for cmd in eval["commands"]:
        print(f"Executing: {cmd}")
        subprocess.run(cmd, shell=True)

    # Switch back to evaluation root directory
    os.chdir(BASE_DIR)


# Run the evaluations
for eval in evaluations:
    # Skip if folder exists
    if os.path.exists(f"./results/{eval['name']}"):
        continue
    run_evaluation(eval)
    wait_until_no_jobs()
