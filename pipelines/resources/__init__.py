"""
Dagster Resources
Reusable resource definitions for connections and clients
"""

from pipelines.resources.cassandra import cassandra_resource
from pipelines.resources.arxiv import arxiv_client_resource

__all__ = [
    "cassandra_resource",
    "arxiv_client_resource",
]
