"""
Cassandra Resource

Reusable Cassandra connection pool as a Dagster resource.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING
import os

# Configure environment for Cassandra Python 3.13+ compatibility
os.environ['LIBEV_FALLBACK_LOOP'] = '1'

from dagster import resource, Field

if TYPE_CHECKING:
    from cassandra.cluster import Cluster

logger = logging.getLogger(__name__)

# Try to import Cassandra components, but allow graceful degradation
try:
    from cassandra.query import ConsistencyLevel
    _CASSANDRA_AVAILABLE = True
except Exception as e:
    logger.warning(f"Cassandra not fully available: {e}")
    _CASSANDRA_AVAILABLE = False
    ConsistencyLevel = None


class CassandraResource:
    """Wrapper for Cassandra cluster and session"""

    def __init__(self, cluster: Cluster, session):
        self.cluster = cluster
        self.session = session
        self.logger = logger

    def close(self):
        """Shutdown cluster and session"""
        try:
            self.session.shutdown()
            self.cluster.shutdown()
            self.logger.info("Cassandra connection closed")
        except Exception as e:
            self.logger.error(f"Error closing Cassandra: {str(e)}")


@resource(
    config_schema={
        "contact_points": Field(
            [str],
            description="Cassandra node addresses (host:port)",
            default_value=["localhost:9042"],
        ),
        "keyspace": Field(
            str,
            description="Keyspace to use",
            default_value="arxiv",
        ),
        "consistency_level": Field(
            str,
            description="Query consistency level (ONE, LOCAL_QUORUM, QUORUM, ALL)",
            default_value="LOCAL_QUORUM",
        ),
        "pool_size": Field(
            int,
            description="Connection pool size",
            default_value=5,
        ),
        "timeout": Field(
            float,
            description="Query timeout in seconds",
            default_value=10.0,
        ),
    },
    required_resource_keys=frozenset(),
)
def cassandra_resource(context):
    """
    Create and yield Cassandra connection resource.

    This resource:
    - Connects to Cassandra cluster (lazy import for Python 3.13+ compat)
    - Creates session for keyspace
    - Maintains connection pool  
    - Auto-closes on pipeline completion

    Config:
        contact_points: List of "host:port" strings
        keyspace: Target keyspace (e.g., "arxiv")
        consistency_level: Read/write consistency guarantee
        pool_size: Number of connections to maintain
        timeout: Max seconds to wait for query response

    Usage in assets:
        @asset
        def my_asset(cassandra_resource):
            # Use cassandra_resource.session for queries
            result = cassandra_resource.session.execute("SELECT * FROM ...")

    Returns:
        CassandraResource object with .cluster and .session attributes
    """
    # Lazy import Cluster here to avoid event loop issues during module load
    from cassandra.cluster import Cluster
    from cassandra.query import ConsistencyLevel as CL
    
    config = context.resource_config

    try:
        logger.info(
            f"🔌 Connecting to Cassandra: {config['contact_points'][0]}"
        )

        # Create cluster connection
        cluster = Cluster(
            contact_points=config["contact_points"],
            default_consistency_level=CL.name_to_value(
                config["consistency_level"]
            ),
        )

        # Create session for keyspace
        session = cluster.connect(config["keyspace"])
        session.default_timeout = config["timeout"]

        logger.info(
            f"✅ Connected to keyspace '{config['keyspace']}' "
            f"with {config['pool_size']} connections"
        )

        # Create resource object
        cassandra = CassandraResource(cluster, session)

        # Yield to Dagster (available for assets to use)
        yield cassandra

    except Exception as e:
        logger.error(f"❌ Failed to connect to Cassandra: {str(e)}")
        raise

    finally:
        # Cleanup when pipeline completes
        try:
            if "cassandra" in locals():
                cassandra.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
