from typing import List, Dict
from dagster import asset, Config, get_dagster_logger
from pydantic import BaseModel, Field

from ingestion.fetch_papers import PaperFetcher

logger = get_dagster_logger()


class FetchArxivConfig(Config):
    """Configuration for fetch operation"""

    batch_size: int = Field(
        default=100,
        description="Number of papers to fetch per API request",
    )
    categories: List[str] = Field(
        default=["cs.AI", "cs.LG", "cs.CV", "cs.CL", "stat.ML"],
        description="arXiv categories to fetch papers from",
    )


@asset(
    name="fetch_arxiv_papers",
    description="Fetch papers from arXiv API by category",
)
def fetch_arxiv_papers(config: FetchArxivConfig) -> List[Dict]:
    """
    Fetch raw papers from arXiv API.

    This asset:
    - Connects to the arXiv API
    - Fetches papers from specified categories
    - Returns raw paper metadata (13 fields)
    - Logs metrics for monitoring

    Args:
        config: FetchArxivConfig with batch_size and categories

    Returns:
        List of raw paper dictionaries with fields:
        - arxiv_id, title, abstract, authors, categories
        - published_date, updated_date, pdf_url, raw_json
        - primary_category, ingested_at, updated_date

    Raises:
        Exception: If API fails after 3 retries (handled by Dagster)

    Example:
        >>> papers = fetch_arxiv_papers(FetchArxivConfig())
        >>> len(papers)
        742
        >>> papers[0].keys()
        dict_keys(['arxiv_id', 'title', 'abstract', ...])
    """
    logger.info(
        f"🔍 Fetching papers from {len(config.categories)} arXiv categories..."
    )

    try:
        # Initialize fetcher with configured batch size
        fetcher = PaperFetcher(batch_size=config.batch_size)

        # Fetch papers from all categories
        raw_papers = fetcher.fetch_papers()

        # Log metrics
        logger.info(f"✅ Fetched {len(raw_papers)} papers from arXiv API")

        # Log breakdown by category (if available in papers)
        category_counts = {}
        for paper in raw_papers:
            for cat in paper.get("categories", []):
                category_counts[cat] = category_counts.get(cat, 0) + 1

        for cat, count in sorted(category_counts.items())[:5]:  # Top 5
            logger.info(f"   • {cat}: {count} papers")

        return raw_papers

    except Exception as e:
        logger.error(f"❌ Failed to fetch papers: {str(e)}")
        # Dagster will automatically retry 3 times
        raise