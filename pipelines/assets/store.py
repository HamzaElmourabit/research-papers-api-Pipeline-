"""
Asset: Store in Cassandra

Inserts validated papers into Cassandra with batch tracking.
"""

from typing import List, Dict
from dagster import asset, Config, get_dagster_logger, In, Nothing
from pydantic import BaseModel, Field

from casandra.insert_papers import insert_papers

logger = get_dagster_logger()


class CassandraStoreConfig(Config):
    """Configuration for Cassandra insertion"""

    chunk_size: int = Field(
        default=25,
        description="Number of papers per insert batch (Cassandra recommends < 100)",
    )
    consistency_level: str = Field(
        default="LOCAL_QUORUM",
        description="Cassandra consistency level for writes",
    )


@asset(
    name="store_in_cassandra",
    description="Insert validated papers into Cassandra",
)
def store_in_cassandra(
    validate_papers: List[Dict],
    config: CassandraStoreConfig,
) -> Dict:
    """
    Insert validated papers into Cassandra papers_raw table.

    This asset:
    - Takes validated papers from validate asset (dependency)
    - Generates batch_id (UUID) for tracking this ingestion run
    - Chunks papers into small batches (size: 25)
    - Inserts into papers_raw table with retry logic
    - Returns summary with metrics

    Args:
        validate_papers: Validated papers from validate asset (dependency)
        config: CassandraStoreConfig with chunk_size and consistency

    Returns:
        Summary Dict with:
        {
            "batch_id": UUID (string),
            "total": int (papers attempted),
            "inserted": int (successful inserts),
            "failed": int (failed inserts),
            "ingestion_date": date string,
            "duration_seconds": float
        }

    Notes:
        - Idempotent: batch_id uniquely tracks this run
        - Handles duplicates: same arxiv_id in same batch → skip
        - Retry logic: 3 retries per chunk with exponential backoff
        - Partial success: some chunks may fail, others succeed
        - On final failure: logs batch_id for manual review

    Table Schema:
        Primary Key: (batch_id, arxiv_id)
        Columns: 13 fields (title, abstract, authors, etc.)

    Example:
        >>> validated = validate_papers(...)
        >>> result = store_in_cassandra(validated)
        >>> result
        {
            'batch_id': '550e8400-e29b-41d4-a716-446655440000',
            'total': 712,
            'inserted': 712,
            'failed': 0,
            'ingestion_date': '2024-03-24',
            'duration_seconds': 45.2
        }
    """
    total_papers = len(validate_papers)
    logger.info(f"💾 Inserting {total_papers} papers into Cassandra...")

    try:
        # Call existing insert_papers function
        # It handles: batch_id generation, chunking, retries, metrics
        summary = insert_papers(
            validate_papers,
            chunk_size=config.chunk_size,
        )

        # Log summary metrics
        inserted = summary.get("inserted", 0)
        failed = summary.get("failed", 0)
        batch_id = summary.get("batch_id", "UNKNOWN")
        duration = summary.get("duration_seconds", 0)

        logger.info(f"✅ Cassandra insertion complete in {duration:.2f}s")
        logger.info(
            f"   • Batch ID: {batch_id}"
        )
        logger.info(
            f"   • Inserted: {inserted}/{total_papers}"
        )

        if failed > 0:
            logger.warning(
                f"⚠️  Failed to insert {failed} papers. "
                f"See batch_id {batch_id} logs for details."
            )
        else:
            logger.info(f"✅ All {inserted} papers successfully stored!")

        return summary

    except Exception as e:
        logger.error(f"❌ Cassandra insertion error: {str(e)}")
        raise
