"""
Dagster Job & Schedule

Defines the daily ingestion job and its schedule.
"""

import logging
from dagster import (
    define_asset_job,
    schedule,
    ScheduleDefinition,
)

logger = logging.getLogger(__name__)

# ============================================================================
# JOB DEFINITION
# ============================================================================

daily_ingestion_job = define_asset_job(
    name="daily_ingestion_job",
    selection=[
        "fetch_arxiv_papers",
        "validate_papers",
        "store_in_cassandra",
    ],
    description="Daily ETL pipeline: Fetch → Validate → Store",
)

"""
Job Definition Notes:
- Name: daily_ingestion_job
- Assets: fetch_arxiv_papers → validate_papers → store_in_cassandra
- Execution: Sequential (each asset waits for previous)
- Retry: 3 attempts per asset (configured in Dagster)
- Backoff: Exponential (30s, 60s, 120s)

Asset Dependencies:
1. fetch_arxiv_papers (no inputs, external data source)
   ↓ (outputs: List[Dict] raw papers)
2. validate_papers (input: fetch_arxiv_papers)
   ↓ (outputs: List[Dict] validated papers)
3. store_in_cassandra (input: validate_papers)
   ↓ (outputs: Dict summary with batch_id)
"""

# ============================================================================
# SCHEDULE DEFINITION
# ============================================================================


@schedule(
    job=daily_ingestion_job,
    cron_schedule="0 2 * * *",  # 2 AM UTC every day
    execution_timezone="UTC",
)
def daily_ingestion_schedule(context):
    """
    Schedule for the daily ingestion pipeline.

    Trigger: Every day at 2:00 AM UTC

    Cron Expression: "0 2 * * *"
    - Minute: 0 (top of hour)
    - Hour: 2 (2 AM)
    - Day: * (every day)
    - Month: * (every month)
    - Weekday: * (every weekday, 0=Sunday)

    When triggered:
    1. Fetch papers from arXiv API (5 categories)
    2. Validate papers (Pydantic schema)
    3. Store in Cassandra (batch tracking)

    Timezone: UTC (for consistency across deployments)

    Returns:
        Empty dict (schedule doesn't pass parameters)

    Notes:
    - Runs at consistent time globally (UTC baseline)
    - Expected duration: 2-5 minutes
    - Results visible in Dagit UI immediately
    - Failures trigger alerts (Slack/Email, if configured)
    """
    return {}


"""
Schedule Details:
- Name: daily_ingestion_schedule
- Frequency: Daily
- Time: 02:00 UTC (2 AM)
- Job: daily_ingestion_job
- Execution Model: Dagster daemon (lightweight, stateless)

Timezone Handling:
- UTC ensures consistent timing across regions
- Local time calculation:
  • 02:00 UTC = 09:00 AM IST (India)
  • 02:00 UTC = 10:00 AM GST (Gulf)
  • 02:00 UTC = 21:00 PM PST (Pacific, day before)

To disable this schedule:
1. Comment out the @schedule decorator
2. Remove from dagster_pipeline.py schedules=[]
3. Manual triggers still work via Dagit

To change time:
- Modify cron_schedule: "0 3 * * *" (3 AM) or "30 1 * * *" (1:30 AM)
"""
