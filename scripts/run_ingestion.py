#!/usr/bin/env python
"""
Run arXiv ingestion pipeline via Dagster

Usage:
    python scripts/run_ingestion.py [local|schedule]

Modes:
    local    - Execute job once immediately
    schedule - Start daemon for scheduled runs
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
MODE = sys.argv[1] if len(sys.argv) > 1 else "local"
# Environment setup
os.environ['PYTHONPATH'] = PROJECT_ROOT + os.pathsep + os.environ.get('PYTHONPATH', '')
os.environ['DAGSTER_HOME'] = os.environ.get('DAGSTER_HOME', os.path.join(PROJECT_ROOT, '.dagster'))
# Create DAGSTER_HOME if it doesn't exist
dagster_home = os.environ['DAGSTER_HOME']
os.makedirs(dagster_home, exist_ok=True)
os.chdir(PROJECT_ROOT)
print("=" * 50)
print("Dagster Ingestion Pipeline")
print("=" * 50)
print(f"Mode: {MODE}")
print(f"Project root: {PROJECT_ROOT}")
print(f"Workspace: {os.getcwd()}")
print()


def run_local():
    """Execute the job once locally"""
    logger.info("Running job locally (one-time execution)...")
    print()
    
    try:
        # Execute using python -m dagster
        cmd = [
            sys.executable, '-m', 'dagster', 'job', 'execute',
            '-f', 'pipelines/dagster_pipeline.py',
            '-j', 'daily_ingestion_job'
        ]
        
        logger.info(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            print()
            logger.info("Job completed successfully!")
            print()
            logger.info("To view detailed results:")
            logger.info("  1. Start Dagit: python scripts/launch_dagit.py")
            logger.info("  2. Visit: http://localhost:3000")
        else:
            logger.error(f"Job failed with return code {result.returncode}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Failed to execute job: {str(e)}")
        sys.exit(1)
def run_schedule():
    """Start the Dagster daemon for scheduled runs"""
    logger.info("Starting Dagster daemon for scheduled runs...")
    print()
    logger.info("The daemon will:")
    logger.info("  - Run daily_ingestion_job every day at 2:00 AM UTC")
    logger.info("  - Monitor schedules and triggers")
    logger.info("  - Handle retries automatically")
    print()
    logger.info("Press Ctrl+C to stop the daemon")
    print()
    
    try:
        # Create storage directory
        dagster_home = os.environ['DAGSTER_HOME']
        os.makedirs(dagster_home, exist_ok=True)
        
        # Start daemon using python -m dagster._daemon
        cmd = [sys.executable, '-m', 'dagster._daemon', 'run']
        
        logger.info(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        
        if result.returncode != 0:
            logger.error(f"Daemon failed with return code {result.returncode}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print()
        logger.info("Daemon stopped by user")
    except Exception as e:
        logger.error(f"Failed to start daemon: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point"""
    if MODE == "local":
        run_local()
    elif MODE == "schedule":
        run_schedule()
    else:
        logger.error(f"Unknown mode: {MODE}")
        print()
        print("Usage: python scripts/run_ingestion.py [local|schedule]")
        print()
        print("Modes:")
        print("  local    - Run job once immediately")
        print("  schedule - Start daemon for daily execution")
        print()
        print("Examples:")
        print("  python scripts/run_ingestion.py local")
        print("  python scripts/run_ingestion.py schedule")
        sys.exit(1)


if __name__ == "__main__":
    main()
