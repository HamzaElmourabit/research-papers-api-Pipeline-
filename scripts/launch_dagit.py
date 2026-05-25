"""
Launch Dagster Dagit UI for the arXiv pipeline

Usage:
    python scripts/launch_dagit.py
"""

import sys
import os
import subprocess
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Environment setup
os.environ['PYTHONPATH'] = PROJECT_ROOT + os.pathsep + os.environ.get('PYTHONPATH', '')
os.environ['DAGSTER_HOME'] = os.environ.get('DAGSTER_HOME', os.path.join(PROJECT_ROOT, '.dagster'))

# Create DAGSTER_HOME if it doesn't exist
dagster_home = os.environ['DAGSTER_HOME']
os.makedirs(dagster_home, exist_ok=True)

os.chdir(PROJECT_ROOT)

print("=" * 50)
print("Launching Dagster Dagit UI")
print("=" * 50)
print()

logger.info(f"Project root: {PROJECT_ROOT}")
logger.info(f"DAGSTER_HOME: {os.environ['DAGSTER_HOME']}")
print()

logger.info("Starting Dagit...")
print()
logger.info("Dagit UI will be available at:")
logger.info("   http://localhost:3000")
print()
logger.info("Press Ctrl+C to stop")
print()

try:
    # Launch Dagit on port 3000 using python -m dagit
    cmd = [
        sys.executable, '-m', 'dagit',
        '-f', 'pipelines/dagster_pipeline.py',
        '-p', '3000'
    ]
    
    logger.info(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=PROJECT_ROOT)
    
except KeyboardInterrupt:
    print()
    logger.info("Dagit stopped by user")
except Exception as e:
    logger.error(f"Failed to start Dagit: {str(e)}")
    logger.error("Make sure dagster and dagit are installed:")
    logger.error("  pip install dagster dagit")
    sys.exit(1)
