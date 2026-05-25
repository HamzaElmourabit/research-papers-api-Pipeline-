"""
Run the full Databricks Spark pipeline sequentially: Bronze, Silver, Gold.
This script is designed to run inside a Spark container or any environment with Spark available.
"""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
scripts = [
    root / "databricks" / "bronze_layer.py",
    root / "databricks" / "silver_layer.py",
    root / "databricks" / "gold_layer.py",
]

if __name__ == "__main__":
    print("Running Spark pipeline: Bronze → Silver → Gold")
    for script in scripts:
        if not script.exists():
            print(f"Error: Script not found: {script}")
            sys.exit(1)

    spark_cmd = [
        "spark-submit",
        "--master",
        "local[2]",
    ]

    for script in scripts:
        print("\n" + "=" * 70)
        print(f"Executing: {script.name}")
        print("=" * 70)
        cmd = spark_cmd + [str(script)]
        print("Command:", " ".join(cmd))
        process = subprocess.Popen(cmd, shell=False)
        process.communicate()
        if process.returncode != 0:
            print(f"ERROR: Script failed: {script.name}")
            sys.exit(process.returncode)

    print("\n✅ Full Spark pipeline completed successfully")
