"""
Dagster Assets
Data products (assets) for the ETL pipeline
"""

from pipelines.assets.fetch import fetch_arxiv_papers
from pipelines.assets.validate import validate_papers
from pipelines.assets.store import store_in_cassandra
from pipelines.assets.export import export_papers_to_parquet

__all__ = [
    "fetch_arxiv_papers",
    "validate_papers",
    "store_in_cassandra",
    "export_papers_to_parquet",
]
