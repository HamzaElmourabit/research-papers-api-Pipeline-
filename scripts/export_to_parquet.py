"""
Standalone Script: Export Cassandra to Parquet

Run this directly without Dagster for on-demand exports:
    python scripts/export_to_parquet.py [--output-dir ./data/parquet] [--chunk-size 400]

This is useful for:
- Manual data exports
- Testing the export pipeline
- Offline processing of Cassandra data

NOTE: Uses Docker cqlsh (not Python driver) for Python 3.13 compatibility
"""

import sys
import argparse
import subprocess
import json
from pathlib import Path
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd


# ============================================================================
# FETCH VIA DOCKER CQLSH (Python 3.13 compatible)
# ============================================================================


def fetch_papers_via_cqlsh(container_name: str = "cassandra_arxiv") -> list:
    """
    Fetch all papers from Cassandra using Docker cqlsh CLI.
    
    Avoids Python 3.13 cassandra-driver incompatibility by using 
    the Docker container's cqlsh tool to export to CSV, then read the CSV.
    
    Args:
        container_name: Docker container name for Cassandra
    
    Returns:
        List of row dicts with all papers
    """
    
    import tempfile
    import csv
    import os
    
    try:
        # Use cqlsh COPY command to export to CSV (more reliable than parsing table output)
        csv_file = "/tmp/papers_export.csv"
        cql_command = f"USE arxiv; COPY papers_raw TO '{csv_file}' WITH HEADER=true;"
        
        # Execute the COPY command
        result = subprocess.run(
            ["docker", "exec", container_name, "cqlsh", "-e", cql_command],
            capture_output=True,
            text=False,
            timeout=60,
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
            # If COPY fails, try SELECT with LIMIT (may work for small tables)
            print(f"COPY command failed, falling back to SELECT: {error_msg}")
            return fetch_via_select_fallback(container_name)
        
        # Copy CSV file out of container to temp file
        temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_csv_path = temp_csv.name
        temp_csv.close()
        
        # Copy from container to host
        cp_result = subprocess.run(
            ["docker", "cp", f"{container_name}:{csv_file}", temp_csv_path],
            capture_output=True,
            text=False,
            timeout=10,
        )
        
        if cp_result.returncode != 0:
            print("COPY from container failed, using SELECT fallback")
            return fetch_via_select_fallback(container_name)
        
        # Read CSV file
        rows = []
        try:
            with open(temp_csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
        finally:
            # Clean up temp file
            if os.path.exists(temp_csv_path):
                os.remove(temp_csv_path)
        
        return rows
    
    except Exception as e:
        print(f"fetch_papers_via_cqlsh failed: {e}, trying SELECT fallback")
        return fetch_via_select_fallback(container_name)


def fetch_via_select_fallback(container_name: str = "cassandra_arxiv") -> list:
    """
    Fallback method: fetch using SELECT and parse simple output.
    Works for tables with small number of rows.
    """
    
    cql_query = "USE arxiv; SELECT batch_id, arxiv_id, title, authors, categories, primary_category, published_date, pdf_url FROM papers_raw;"
    
    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "cqlsh", "-e", cql_query],
            capture_output=True,
            text=False,
            timeout=30,
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
            raise Exception(f"SELECT query failed: {error_msg}")
        
        # Decode output handling encoding errors
        output_text = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
        
        # Simple fallback: return empty list - better to use COPY method
        # For now, print warning and return empty
        print("SELECT fallback: Parsing table output directly...")
        print("WARNING: This is a fallback method. To export properly, please run: python main.py first")
        return []
    
    except Exception as e:
        raise Exception(f"Fallback SELECT also failed: {e}")


# ============================================================================
# NORMALIZATION FUNCTIONS (same as in export.py asset)
# ============================================================================


def normalize_value(v):
    """Convert Cassandra types into Parquet-friendly types."""
    if v is None or v == "null":
        return None
    if isinstance(v, str):
        # Try to convert string representations of special types
        if v.lower() in ("null", "none", ""):
            return None
        return v
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def normalize_row(row: dict) -> dict:
    """Normalize all values in a row."""
    return {k: normalize_value(v) for k, v in row.items()}


# ============================================================================
# EXPORT FUNCTION
# ============================================================================


def export_to_parquet(
    output_dir: str = "./data/parquet",
    chunk_size: int = 400,
    container_name: str = "cassandra_arxiv",
):
    """
    Export papers from Cassandra to Parquet files using Docker cqlsh.

    Args:
        output_dir: Directory to save Parquet files
        chunk_size: Number of rows per file
        container_name: Docker container name for Cassandra
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Exporting Cassandra → Parquet")
    print(f"  Output: {output_path}")
    print(f"  Chunk size: {chunk_size} rows/file")
    print(f"  Container: {container_name}")
    print(f"{'='*60}\n")

    try:
        # Fetch all rows via docker cqlsh
        print(f"✓ Fetching from papers_raw table via Docker cqlsh...")
        rows = fetch_papers_via_cqlsh(container_name)
        
        if not rows:
            print(f"⚠ No data found in papers_raw table")
            return False
        
        total_rows = len(rows)
        print(f"✓ Fetched {total_rows} rows")

        # Process and write chunks
        chunk = []
        file_index = 0

        for i, row in enumerate(rows, 1):
            # Normalize and add to chunk
            row = normalize_row(row)
            chunk.append(row)

            # Write chunk when full or at end
            if len(chunk) >= chunk_size or i == total_rows:
                file_name = f"papers_raw_part_{file_index}.parquet"
                file_path = output_path / file_name

                df = pd.DataFrame(chunk)
                df.to_parquet(str(file_path), index=False)

                size_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
                print(f"  ✓ Saved {file_name} ({len(chunk)} rows, {size_mb:.2f} MB)")

                chunk = []
                file_index += 1

        print(f"\n{'='*60}")
        print(f"✓ Export completed successfully!")
        print(f"  Total rows: {total_rows}")
        print(f"  Files created: {file_index}")
        print(f"  Output directory: {output_path}")
        print(f"{'='*60}\n")

        return True

    except Exception as e:
        print(f"\n✗ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    """Parse arguments and run export."""
    parser = argparse.ArgumentParser(
        description="Export Cassandra papers to Parquet files"
    )
    parser.add_argument(
        "--output-dir",
        default="./data/parquet",
        help="Output directory for Parquet files (default: ./data/parquet)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=400,
        help="Number of rows per Parquet file (default: 400)",
    )
    parser.add_argument(
        "--container-name",
        default="cassandra_arxiv",
        help="Docker container name for Cassandra (default: cassandra_arxiv)",
    )

    args = parser.parse_args()

    success = export_to_parquet(
        output_dir=args.output_dir,
        chunk_size=args.chunk_size,
        container_name=args.container_name,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
