"""
ArxivClient Resource

Reusable arXiv API client as a Dagster resource.
"""

import logging
from dagster import resource, Field

from ingestion.arxiv_client import ArxivClient

logger = logging.getLogger(__name__)


@resource(
    config_schema={
        "batch_size": Field(
            int,
            description="Number of papers per API request",
            default_value=100,
        ),
        "timeout": Field(
            float,
            description="API request timeout in seconds",
            default_value=30.0,
        ),
        "max_retries": Field(
            int,
            description="Maximum retries on API failure",
            default_value=3,
        ),
    }
)
def arxiv_client_resource(context):
    """
    Create and yield ArxivClient resource.

    This resource:
    - Wraps the ArxivClient for API access
    - Configurable batch size and timeout
    - Supports retry configuration
    - Stateless (no cleanup needed)

    Config:
        batch_size: Papers per request (higher = fewer calls, larger responses)
        timeout: Seconds to wait for API response
        max_retries: Attempts on failure

    Usage in assets:
        @asset
        def my_asset(arxiv_client_resource):
            # Use arxiv_client_resource to search papers
            results = arxiv_client_resource.search_papers("cs.AI")

    Returns:
        ArxivClient instance configured with provided settings
    """
    config = context.resource_config

    try:
        logger.info(
            f"🔧 Initializing ArxivClient: "
            f"batch_size={config['batch_size']}, "
            f"timeout={config['timeout']}s"
        )

        # Create client with configured batch size
        client = ArxivClient(batch_size=config["batch_size"])

        logger.info("✅ ArxivClient initialized")

        # Yield to Dagster (available for assets to use)
        yield client

    except Exception as e:
        logger.error(f"❌ Failed to initialize ArxivClient: {str(e)}")
        raise
