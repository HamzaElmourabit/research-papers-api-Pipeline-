#!/usr/bin/env python
"""
Cassandra Setup Script
Starts Cassandra via Docker, applies schema, and verifies connection.
"""

import subprocess
import time
import sys
import os


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")
    print(f"Running: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print("Make sure Docker is installed and in your PATH")
        return False

def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          CASSANDRA SETUP FOR ARXIV RESEARCH PAPERS PIPELINE                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

This script will:
1. Start Cassandra 5.0 using Docker
2. Wait for Cassandra to be ready (up to 5 minutes)
3. Copy and execute the schema (arkiv keyspace + papers_raw table)
4. Verify connection
5. Provide instructions for running the pipeline

Prerequisites:
- Docker must be installed and running
- Port 9042 should be available (Cassandra CQL port)

""")
    
    # Step 1: Start Cassandra
    os.chdir(PROJECT_ROOT)
    if not run_command(
        ["docker", "compose", "up", "-d"],
        "STEP 1: Starting Cassandra container..."
    ):
        print("\n⚠️  Failed to start Cassandra. Make sure Docker is running.")
        return False
    
    # Step 2: Wait for Cassandra to be ready
    print(f"\n{'='*70}")
    print("STEP 2: Waiting for Cassandra to be ready...")
    print(f"{'='*70}\n")
    
    for attempt in range(60):  # Try for up to 10 minutes
        try:
            result = subprocess.run(
                ["docker", "exec", "cassandra_arxiv", "cqlsh", "-e", "describe cluster"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✅ Cassandra is ready!")
                print(result.stdout)
                break
        except Exception as e:
            pass
        
        if attempt % 6 == 0:  # Print every 6 attempts (~30 seconds)
            print(f"   Waiting... ({attempt} seconds elapsed)")
        time.sleep(1)
    else:
        print("❌ Cassandra did not become ready within timeout")
        return False
    
    # Step 3: Apply schema
    print(f"\n{'='*70}")
    print("STEP 3: Creating keyspace and tables...")
    print(f"{'='*70}\n")
    
    schema_path = os.path.join(PROJECT_ROOT, "casandra", "schema.cql")
    try:
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        # Execute schema line by line
        for statement in schema.split(';'):
            statement = statement.strip()
            if statement:
                cmd = f'cqlsh -e "{statement}"'
                result = subprocess.run(
                    ["docker", "exec", "cassandra_arxiv", "cqlsh", "-e", statement],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    print(f"⚠️  Warning executing: {statement[:50]}...")
                    if result.stderr:
                        print(f"   Error: {result.stderr[:100]}")
    except Exception as e:
        print(f"❌ Error reading schema: {e}")
        return False
    
    # Step 4: Verify schema
    print(f"\n{'='*70}")
    print("STEP 4: Verifying schema...")
    print(f"{'='*70}\n")
    
    if run_command(
        ["docker", "exec", "cassandra_arxiv", "cqlsh", "-e", "USE arxiv; DESCRIBE TABLE papers_raw;"],
        "Checking papers_raw table..."
    ):
        print("✅ Schema successfully applied!")
    else:
        print("⚠️  Warning: Could not verify table. It may still have been created.")
    
    # Summary
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         SETUP COMPLETE                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

✅ Cassandra is running and ready!

CASSANDRA STATUS:
- Container: cassandra_arxiv
- Port: 9042 (CQL)
- Keyspace: arxiv
- Table: papers_raw
- Replication Factor: 1 (for local development)

NEXT STEPS:
1. Run the full ETL pipeline:
   python scripts/run_ingestion.py local

2. Monitor in Dagit UI (optional):
   python scripts/launch_dagit.py
   then visit http://localhost:3000

3. Query results in Cassandra:
   docker exec -it cassandra_arxiv cqlsh
   USE arxiv;
   SELECT COUNT(*) FROM papers_raw;

USEFUL DOCKER COMMANDS:
- View logs:    docker logs cassandra_arxiv
- Stop:         docker compose down
- Destroy:      docker compose down -v
- Restart:      docker compose restart

""")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
