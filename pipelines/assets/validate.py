"""
Asset: Validate Papers

Validates papers using Pydantic schema, drops invalid records.
"""

from typing import List, Dict
from dagster import asset, Config, get_dagster_logger
from pydantic import BaseModel, Field
from ingestion.validation import validate_paper

logger = get_dagster_logger()


class ValidateConfig(Config):
    """Configuration for validation"""

    drop_invalid: bool = Field(
        default=True,
        description="Drop invalid records (True) or raise on first error (False)",
    )


@asset(
    name="validate_papers",
    description="Validate papers using Pydantic schema",
)
def validate_papers(
    fetch_arxiv_papers: List[Dict],
    config: ValidateConfig,
) -> List[Dict]:
    """
    Validate papers against Pydantic PaperModel schema.

    This asset:
    - Takes raw papers from fetch asset (dependency injection)
    - Applies Pydantic validation (non-empty fields, valid types, etc.)
    - Drops invalid records (non-blocking)
    - Logs validation metrics
    - Alerts if dropout rate is too high (> 15%)

    Args:
        fetch_arxiv_papers: Raw papers from fetch asset (dependency)
        config: ValidateConfig with drop_invalid flag

    Returns:
        List of validated paper dictionaries (subset of input)
        All invalid papers are dropped

    Notes:
        - Non-blocking: partial success allowed
        - Dropped papers logged for quality review
        - Validation schema enforces:
          • Non-empty: arxiv_id, title, abstract, primary_category
          • Non-empty lists: authors, categories
          • Valid datetime: published_date, updated_date
          • Valid URL: pdf_url

    Example:
        >>> raw = fetch_arxiv_papers(FetchArxivConfig())
        >>> valid = validate_papers(raw, ValidateConfig())
        >>> len(raw)
        742
        >>> len(valid)
        712
    """
    total_papers = len(fetch_arxiv_papers)
    logger.info(f"🔍 Validating {total_papers} papers...")

    try:
        # Use existing validation function
        validated_papers = validate_paper(fetch_arxiv_papers)

        # Calculate metrics
        valid_count = len(validated_papers)
        dropped_count = total_papers - valid_count
        dropout_rate = (
            (dropped_count / total_papers * 100)
            if total_papers > 0
            else 0
        )

        # Log results
        logger.info(
            f"✅ Validation complete: {valid_count}/{total_papers} papers valid"
        )
        logger.info(
            f"   • Dropped: {dropped_count} ({dropout_rate:.1f}%)"
        )

        # Alert if loss is too high
        if dropout_rate > 15:
            logger.warning(
                f"⚠️  High validation loss ({dropout_rate:.1f}% > 15%). "
                f"Check data quality at source (arXiv API)."
            )
        elif dropped_count > 0:
            logger.info(
                f"ℹ️  {dropped_count} records dropped due to validation errors"
            )

        return validated_papers

    except Exception as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise
