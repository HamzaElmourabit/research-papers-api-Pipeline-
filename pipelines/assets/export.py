"""
Asset: Export from Cassandra to Parquet (FIXED)

Fix applied:
- Convert list/array → string to ensure Parquet compatibility with Spark/Photon
"""

import subprocess
from datetime import datetime, date
from typing import Dict
from pathlib import Path

import pandas as pd
from dagster import asset, Config, get_dagster_logger
from pydantic import BaseModel, Field

logger = get_dagster_logger()


class ExportToParquetConfig(Config):
    """Configuration for Parquet export"""

    chunk_size: int = Field(
        default=400,
        description="Number of rows per Parquet file",
    )
    output_dir: str = Field(
        default="./data/parquet",
        description="Output directory for Parquet files",
    )


# ============================================================================
# NORMALIZATION FUNCTIONS (FIXED)
# ============================================================================

def normalize_value(v):
    """
    Convert Cassandra/Python complex types into Parquet-friendly types.
    """

    if v is None:
        return None

    # UUID → string
    if hasattr(v, "hex"):
        return str(v)

    # datetime / date → ISO string
    if isinstance(v, (datetime, date)):
        return v.isoformat()

    # Cassandra custom types → string
    if "Date" in str(type(v)):
        return str(v)

    # 🔥 FIX CRITIQUE : convertir les listes en string
    if isinstance(v, list):
        return ",".join(str(x) for x in v)

    return v


def normalize_row(row: dict) -> dict:
    return {k: normalize_value(v) for k, v in row.items()}


# ============================================================================
# CASSANDRA FETCH VIA DOCKER
# ============================================================================

def fetch_papers_via_docker(container_name: str = "cassandra_arxiv") -> list:

    cql_query = "USE arxiv; SELECT * FROM papers_raw;"

    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "cqlsh", "-e", cql_query],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise Exception(f"CQL query failed: {result.stderr}")

        output_lines = result.stdout.strip().split("\n")
        if len(output_lines) < 2:
            return []

        header_line = output_lines[0]
        columns = [col.strip() for col in header_line.split("|")]

        rows = []
        for line in output_lines[2:]:
            if line.strip() and "-" not in line:
                values = [val.strip() for val in line.split("|")]
                if len(values) == len(columns):
                    row = dict(zip(columns, values))
                    rows.append(row)

        return rows

    except subprocess.TimeoutExpired:
        raise Exception(f"Docker exec timed out (container: {container_name})")
    except Exception as e:
        raise Exception(f"Failed to fetch papers: {e}")


# ============================================================================
# EXPORT ASSET
# ============================================================================

@asset(
    name="export_papers_to_parquet",
    description="Export all papers from Cassandra to Parquet files",
    compute_kind="parquet",
)
def export_papers_to_parquet(config: ExportToParquetConfig) -> Dict:

    output_path = Path(config.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting Cassandra → Parquet export to {output_path}")

    try:
        # Fetch data
        logger.info("✓ Fetching papers from Cassandra via Docker cqlsh...")
        rows = fetch_papers_via_docker()

        if not rows:
            logger.warning("⚠ No data found in papers_raw table")
            return {
                "total_rows": 0,
                "files_created": 0,
                "output_dir": str(output_path),
                "export_timestamp": datetime.now().isoformat(),
                "status": "success (empty table)",
            }

        total_rows = len(rows)
        logger.info(f"✓ Fetched {total_rows} rows")

        chunk = []
        file_index = 0

        for i, row in enumerate(rows, 1):
            row = normalize_row(row)
            chunk.append(row)

            if len(chunk) >= config.chunk_size or i == total_rows:
                file_name = f"papers_raw_part_{file_index}.parquet"
                file_path = output_path / file_name

                df = pd.DataFrame(chunk)

                # ✅ écriture propre
                df.to_parquet(str(file_path), index=False)

                size_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
                logger.info(
                    f"  → Saved {file_name} ({len(chunk)} rows, {size_mb:.2f} MB)"
                )

                chunk = []
                file_index += 1

        logger.info(f"✓ Export completed")
        logger.info(f"  Total rows: {total_rows}")
        logger.info(f"  Files created: {file_index}")

        return {
            "total_rows": total_rows,
            "files_created": file_index,
            "output_dir": str(output_path),
            "export_timestamp": datetime.now().isoformat(),
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Export failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            "total_rows": 0,
            "files_created": 0,
            "output_dir": str(output_path),
            "export_timestamp": datetime.now().isoformat(),
            "status": f"error: {str(e)}",
        }
