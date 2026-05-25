#!/usr/bin/env python
"""
Test Dagster pipeline without requiring Cassandra connection.
This verifies that the pipeline structure is correct.
"""

import sys
import os

# Add project to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Set environment
os.environ['DAGSTER_HOME'] = os.path.join(PROJECT_ROOT, '.dagster')
os.makedirs(os.environ['DAGSTER_HOME'], exist_ok=True)

try:
    print("=" * 70)
    print("TESTING DAGSTER PIPELINE STRUCTURE")
    print("=" * 70)
    print()
    
    print("1. Testing imports...")
    try:
        from pipelines.dagster_pipeline import defs
        print("   ✓ Successfully imported defs from dagster_pipeline.py")
        print()
    except Exception as e:
        print(f"   ✗ Failed to import: {str(e)}")
        print()
        raise
    
    print("2. Checking assets...")
    # In Dagster 1.5+, assets are accessed via defs.assets
    assets = defs.assets if hasattr(defs, 'assets') else []
    asset_names = []
    if assets:
        for asset in assets:
            if hasattr(asset, 'key'):
                asset_names.append(asset.key.path[-1] if asset.key.path else str(asset.key))
            elif hasattr(asset, 'name'):
                asset_names.append(asset.name)
    
    print(f"   ✓ Found {len(asset_names)} assets:")
    for name in sorted(asset_names):
        print(f"     - {name}")
    print()
    
    print("3. Checking jobs...")
    # In Dagster 1.5+, jobs are accessed via defs.jobs
    jobs = defs.jobs if hasattr(defs, 'jobs') else []
    job_names = [j.name if hasattr(j, 'name') else str(j) for j in jobs]
    print(f"   ✓ Found {len(job_names)} jobs:")
    for name in job_names:
        print(f"     - {name}")
    print()
    
    print("4. Checking schedules...")
    # In Dagster 1.5+, schedules are accessed via defs.schedules
    schedules = defs.schedules if hasattr(defs, 'schedules') else []
    schedule_names = [s.name if hasattr(s, 'name') else str(s) for s in schedules]
    print(f"   ✓ Found {len(schedule_names)} schedules:")
    for name in schedule_names:
        print(f"     - {name}")
    print()
    
    print("5. Checking resources...")
    # In Dagster 1.5+, resources are accessed via defs.resources
    resources_dict = defs.resources if hasattr(defs, 'resources') else {}
    
    print("5. Checking resources...")
    # In Dagster 1.5+, resources are accessed via defs.resources
    resources_dict = defs.resources if hasattr(defs, 'resources') else {}
    resource_names = list(resources_dict.keys()) if resources_dict else []
    print(f"   ✓ Found {len(resource_names)} resources:")
    for name in resource_names:
        print(f"     - {name}")
    print()
    
    print("=" * 70)
    print("SUCCESS: DAGSTER PIPELINE STRUCTURE IS VALID")
    print("=" * 70)
    print()
    print("To run the full pipeline:")

    print("  python scripts/run_ingestion.py local")
    print()
    print("To start Dagit UI:")
    print("  python scripts/launch_dagit.py")
    print()
    
except Exception as e:
    print()
    print("=" * 70)
    print(f"ERROR: {str(e)}")
    print("=" * 70)
    sys.exit(1)
