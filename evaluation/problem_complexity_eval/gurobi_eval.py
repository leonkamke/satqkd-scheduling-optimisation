import subprocess
from pathlib import Path

# Path to the folder containing JSON files
json_dir = Path("")

# Path to the script to run
script_to_run = Path("")

# Make sure the script and folder exist
if not json_dir.is_dir():
    raise FileNotFoundError(f"Directory not found: {json_dir}")

if not script_to_run.is_file():
    raise FileNotFoundError(f"Script not found: {script_to_run}")

# Insert problem instances to solve
json_files = []

working_dir = Path("")

# Iterate over all .json files in the directory
for json_file in json_files:
    print(f"Processing {json_file}...")
    result = subprocess.run(
        ["python", "-m", "src.solvers.gurobi_solver", str(json_file)],
        capture_output=True,
        text=True,
        check=True,
        cwd=working_dir,
    )
    print(result.stdout)
