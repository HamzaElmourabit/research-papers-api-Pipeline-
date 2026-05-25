# Dagster Pipeline Code Structure - Design Phase

**Phase 1 Design Document** | Implementation Blueprint

---

## Project File Structure

This is how you'll organize your Dagster code in Phase 4:

```
pipelines/
├── __init__.py                    # Package init
├── DESIGN.md                      # This file (planning)
├── config.yaml                    # Configuration template
├── dagster_pipeline.py            # Main entry point (imports & exposes defs)
│
├── assets/                        # Dagster Assets (data products)
│   ├── __init__.py
│   ├── fetch.py                   # Asset: fetch_arxiv_papers
│   ├── validate.py                # Asset: validate_papers
│   └── store.py                   # Asset: store_in_cassandra
│
├── resources/                     # Reusable Resources (connections)
│   ├── __init__.py
│   ├── cassandra.py               # CassandraResource
│   └── arxiv.py                   # ArxivClientResource
│
└── jobs/                          # Job Definitions (scheduling)
    ├── __init__.py
    └── ingestion_job.py           # Job: daily_ingestion_job
```

---

## Asset Definitions

### **Asset 1: `fetch_arxiv_papers`** (`assets/fetch.py`)

**Purpose**: Fetch raw papers from arXiv API

**Code Structure**:
```python
# assets/fetch.py
from dagster import asset, Output, Config
from ingestion.fetch_papers import PaperFetcher
from typing import List, Dict

class FetchArxivConfig(Config):
    """Configuration for fetch operation"""
    batch_size: int = 100
    categories: List[str] = ["cs.AI", "cs.LG", "cs.CV", "cs.CL", "stat.ML"]

@asset(
    name="fetch_arxiv_papers",
    description="Fetch papers from arXiv API by category",
    tags=["ETL", "ingestion", "external-api"],
)
def fetch_arxiv_papers(config: FetchArxivConfig) -> List[Dict]:
    """
    Fetch raw papers from arXiv API.
    
    Returns:
        List of raw paper dictionaries with fields:
        - arxiv_id, title, abstract, authors, categories
        - published_date, updated_date, pdf_url, raw_json
    
    Raises:
        Exception: If API fails after 3 retries
    """
    fetcher = PaperFetcher(batch_size=config.batch_size)
    
    # This calls the existing code from ingestion/fetch_papers.py
    raw_papers = fetcher.fetch_papers()
    
    # Log output metrics
    print(f"Fetched {len(raw_papers)} papers from {len(config.categories)} categories")
    
    return raw_papers
```

**Interface Contract**:
- **Input**: None (external API)
- **Output**: `List[Dict]` with 13 fields
- **Size**: ~500-1000 papers per run
- **Errors**: Raised to Dagster for automated retry

---

### **Asset 2: `validate_papers`** (`assets/validate.py`)

**Purpose**: Validate raw papers using Pydantic schema

**Code Structure**:
```python
# assets/validate.py
from dagster import asset, Config, DynamicOut, DynamicOutput
from ingestion.validation import validate_paper, PaperModel
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class ValidateConfig(Config):
    """Configuration for validation"""
    drop_invalid: bool = True  # Drop or raise on invalid?

@asset(
    name="validate_papers",
    description="Validate papers using Pydantic schema",
    tags=["ETL", "validation", "data-quality"],
)
def validate_papers(
    fetch_arxiv_papers: List[Dict],
    config: ValidateConfig
) -> List[Dict]:
    """
    Validate papers against Pydantic PaperModel.
    
    Args:
        fetch_arxiv_papers: Raw papers from fetch asset
        config: Validation configuration
    
    Returns:
        List of validated paper dictionaries
        (invalid papers dropped silently)
    
    Logs:
        Validation errors for dropped papers
    """
    # Use existing validation function
    validated_papers = validate_paper(fetch_arxiv_papers)
    
    # Metrics
    total = len(fetch_arxiv_papers)
    valid = len(validated_papers)
    dropped = total - valid
    
    logger.info(
        f"Validation complete: {valid}/{total} papers valid, "
        f"{dropped} dropped ({100*dropped/total:.1f}%)"
    )
    
    # Alert if loss too high
    if dropped / total > 0.15:  # > 15% loss
        logger.warning(
            f"High validation loss: {100*dropped/total:.1f}%. "
            f"Check data quality at source."
        )
    
    return validated_papers
```

**Interface Contract**:
- **Input**: `List[Dict]` from fetch_arxiv_papers
- **Output**: `List[Dict]` (subset of input, no schema changes)
- **Size**: ~450-950 papers (5-10% drop)
- **Errors**: Non-blocking (logged, partial success allowed)

---

### **Asset 3: `store_in_cassandra`** (`assets/store.py`)

**Purpose**: Insert validated papers into Cassandra

**Code Structure**:
```python
# assets/store.py
from dagster import asset, Config, get_dagster_logger
from casandra.insert_papers import insert_papers
from typing import List, Dict
import uuid

logger = get_dagster_logger()

class CassandraConfig(Config):
    """Configuration for Cassandra insertion"""
    chunk_size: int = 25
    consistency_level: str = "LOCAL_QUORUM"

@asset(
    name="store_in_cassandra",
    description="Insert validated papers into Cassandra",
    tags=["ETL", "database", "cassandra"],
    io_managers_def={},  # No I/O manager (database is sink)
)
def store_in_cassandra(
    validate_papers: List[Dict],
    cassandra_resource,  # Resource injection
    config: CassandraConfig,
) -> Dict:
    """
    Insert validated papers into Cassandra papers_raw table.
    
    Args:
        validate_papers: Validated papers from validate asset
        cassandra_resource: Injected Cassandra connection
        config: Insertion configuration
    
    Returns:
        Summary dict with batch metadata:
        {
            "batch_id": UUID,
            "total": int,
            "inserted": int,
            "failed": int,
            "duration_seconds": float,
            "ingestion_date": date
        }
    
    Raises:
        Exception: If all chunks fail after retries
    """
    # Use existing insert function
    summary = insert_papers(
        validate_papers,
        chunk_size=config.chunk_size
    )
    
    # Log summary
    logger.info(
        f"Cassandra insertion complete: "
        f"batch_id={summary['batch_id']}, "
        f"inserted={summary['inserted']}/{summary['total']}, "
        f"failed={summary['failed']}"
    )
    
    # Detailed metrics
    if summary['failed'] > 0:
        logger.warning(
            f"Some papers failed to insert. "
            f"See batch_id {summary['batch_id']} for details."
        )
    
    return summary
```

**Interface Contract**:
- **Input**: `List[Dict]` from validate_papers
- **Output**: `Dict` summary (batch_id, counts, timestamps)
- **Idempotency**: Batch ID tracks each run uniquely
- **Errors**: May partially succeed (chunk-level retries)

---

## Resource Definitions

### **Cassandra Resource** (`resources/cassandra.py`)

**Purpose**: Reusable Cassandra connection pool

**Code Structure**:
```python
# resources/cassandra.py
from dagster import resource, Field, StringSource, IntSource
from cassandra.cluster import Cluster
from cassandra.query import ConsistencyLevel
import logging

logger = logging.getLogger(__name__)

class CassandraResource:
    def __init__(self, cluster, session):
        self.cluster = cluster
        self.session = session
    
    def close(self):
        self.session.shutdown()
        self.cluster.shutdown()

@resource(
    config_schema={
        "contact_points": Field(
            [str],
            description="Cassandra node addresses",
            default_value=["localhost:9042"]
        ),
        "keyspace": Field(
            str,
            description="Keyspace to use",
            default_value="arxiv"
        ),
        "consistency_level": Field(
            str,
            description="Query consistency level",
            default_value="LOCAL_QUORUM"
        ),
        "pool_size": Field(
            int,
            description="Connection pool size",
            default_value=5
        ),
        "timeout": Field(
            float,
            description="Query timeout in seconds",
            default_value=10.0
        ),
    },
    required_resource_keys=[],
)
def cassandra_resource(context):
    """
    Create and yield Cassandra connection resource.
    Automatically closes on context exit.
    """
    config = context.resource_config
    
    try:
        cluster = Cluster(
            contact_points=config["contact_points"],
            default_consistency_level=ConsistencyLevel.name_to_value(
                config["consistency_level"]
            )
        )
        session = cluster.connect(config["keyspace"])
        session.default_timeout = config["timeout"]
        
        logger.info(
            f"Cassandra connected to {config['contact_points']}, "
            f"keyspace={config['keyspace']}"
        )
        
        yield CassandraResource(cluster, session)
        
    finally:
        # Cleanup
        resource.close()
        logger.info("Cassandra connection closed")
```

**Configuration** (in `config.yaml`):
```yaml
resources:
  cassandra_resource:
    config:
      contact_points:
        - "localhost:9042"
      keyspace: "arxiv"
      consistency_level: "LOCAL_QUORUM"
      pool_size: 5
      timeout: 10.0
```

---

### **ArxivClient Resource** (`resources/arxiv.py`)

**Purpose**: Reusable arXiv API client

**Code Structure**:
```python
# resources/arxiv.py
from dagster import resource, Field
from ingestion.arxiv_client import ArxivClient
import logging

logger = logging.getLogger(__name__)

@resource(
    config_schema={
        "batch_size": Field(
            int,
            description="Papers per API request",
            default_value=100
        ),
        "timeout": Field(
            float,
            description="API request timeout in seconds",
            default_value=30.0
        ),
        "max_retries": Field(
            int,
            description="Max retries on API failure",
            default_value=3
        ),
    }
)
def arxiv_client_resource(context):
    """
    Create and yield ArxivClient resource.
    Client is stateless, no cleanup needed.
    """
    config = context.resource_config
    
    client = ArxivClient(batch_size=config["batch_size"])
    # Set timeout on client (if supported)
    
    logger.info(f"ArxivClient initialized: batch_size={config['batch_size']}")
    
    yield client
```

---

## Job Definition

### **Daily Ingestion Job** (`jobs/ingestion_job.py`)

**Purpose**: Define the full pipeline with scheduling

**Code Structure**:
```python
# jobs/ingestion_job.py
from dagster import (
    define_asset_job,
    schedule,
    ScheduleDefinition,
    DefaultSensorDefinition,
    job,
    op,
)
from dagster._core.storage.dagster_run import DagsterRun
from datetime import datetime, time
import pytz

# Define the job (3 assets in sequence)
daily_ingestion_job = define_asset_job(
    name="daily_ingestion_job",
    selection=["fetch_arxiv_papers", "validate_papers", "store_in_cassandra"],
    tags={
        "owner": "data-engineering",
        "team": "analytics",
        "sla": "2:00 AM UTC",
    },
)

# Define the schedule (every day at 2:00 AM UTC)
@schedule(
    job=daily_ingestion_job,
    cron_schedule="0 2 * * *",  # 2 AM UTC every day
    execution_timezone="UTC",
)
def daily_ingestion_schedule(context):
    """
    Schedule daily ingestion pipeline at 2:00 AM UTC.
    
    Frequency: Every day
    Time: 02:00 UTC (midnight + 2 hours)
    
    This schedule automatically triggers a run of:
    1. fetch_arxiv_papers
    2. validate_papers
    3. store_in_cassandra
    """
    return {}

# Alternative: Manual trigger sensor
@sensor(job=daily_ingestion_job)
def manual_trigger_sensor(context):
    """
    Optional: Sensor for manual/on-demand triggers.
    Useful for backfills or testing.
    """
    # TODO: Implement manual trigger logic if needed
    pass
```

---

## Main Pipeline Entrypoint

### **Dagster Pipeline Definition** (`dagster_pipeline.py`)

**Purpose**: Expose all definitions to Dagit

**Code Structure**:
```python
# dagster_pipeline.py
from dagster import Definitions, load_assets_from_package_module

from pipelines import assets, resources, jobs
from pipelines.jobs.ingestion_job import (
    daily_ingestion_job,
    daily_ingestion_schedule,
)

# Load all assets from the assets package
all_assets = load_assets_from_package_module(assets)

# Create definitions (Dagster's main object)
defs = Definitions(
    assets=all_assets,
    resources={
        "cassandra_resource": resources.cassandra_resource,
        "arxiv_client_resource": resources.arxiv_client_resource,
    },
    jobs=[daily_ingestion_job],
    schedules=[daily_ingestion_schedule],
)

# Dagit will load this object
if __name__ == "__main__":
    # For local development:
    # dagit -f dagster_pipeline.py
    pass
```

---

## Configuration Template

### **`pipelines/config.yaml`**

**Purpose**: Define runtime configurations for assets & resources

**Structure**:
```yaml
# pipelines/config.yaml

# Global resource configuration
resources:
  cassandra_resource:
    config:
      contact_points:
        - "localhost:9042"
      keyspace: "arxiv"
      consistency_level: "LOCAL_QUORUM"
      pool_size: 5
      timeout: 10.0
  
  arxiv_client_resource:
    config:
      batch_size: 100
      timeout: 30.0
      max_retries: 3

# Asset-specific configuration
ops:
  fetch_arxiv_papers:
    config:
      batch_size: 100
      categories:
        - "cs.AI"
        - "cs.LG"
        - "cs.CV"
        - "cs.CL"
        - "stat.ML"
  
  validate_papers:
    config:
      drop_invalid: true

  store_in_cassandra:
    config:
      chunk_size: 25
      consistency_level: "LOCAL_QUORUM"

# Job configuration
jobs:
  daily_ingestion_job:
    # Resources for this job
    resource_defs:
      cassandra_resource: ...
    
    # Hooks (on success/failure)
    hooks:
      - success_hook
      - failure_hook

# Logging
logging:
  version: 1
  formatters:
    default:
      format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  handlers:
    default:
      class: logging.StreamHandler
      formatter: default
  root:
    level: INFO
    handlers:
      - default
```

---

## Error Handling Strategy (Code Level)

### **Retry Policy** (Dagster Native)

Apply to each asset:
```python
from dagster import Backoff, Jitter

@asset(
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=30,  # seconds
        backoff=Backoff.EXPONENTIAL,
        jitter=Jitter.FULL,
    )
)
def fetch_arxiv_papers(...):
    ...
```

### **Hooks** (On Success/Failure)

```python
# pipelines/jobs/hooks.py
from dagster import success_hook, failure_hook

@success_hook
def success_hook(context):
    """Log or notify on successful run"""
    logger.info(f"Pipeline run {context.run_id} succeeded")

@failure_hook
def failure_hook(context):
    """Log or notify on failed run"""
    logger.error(f"Pipeline run {context.run_id} failed")
    # TODO: Send Slack/Email notification
```

---

## Testing Strategy (Phase 4)

When implementing, write unit tests:

```python
# tests/test_assets.py
from dagster import build_op_context
from pipelines.assets.fetch import fetch_arxiv_papers
from pipelines.assets.validate import validate_papers

def test_fetch_with_mock_api():
    """Mock arXiv API and test fetch asset"""
    # TODO: Mock PaperFetcher
    result = fetch_arxiv_papers(config=...)
    assert len(result) > 0
    assert all("arxiv_id" in r for r in result)

def test_validate_filters_invalid():
    """Test validation filters invalid papers"""
    raw_papers = [{invalid: "paper"}]  # Missing fields
    result = validate_papers(raw_papers)
    assert len(result) == 0  # Dropped

def test_e2e_pipeline(cassandra_fixture):
    """Integration test with real Cassandra"""
    # TODO: Use test Cassandra instance
    pass
```

---

## Summary Table

| Component | File | Class/Function | Responsibility |
|-----------|------|-----------------|-----------------|
| Asset 1 | `assets/fetch.py` | `fetch_arxiv_papers()` | Fetch from API |
| Asset 2 | `assets/validate.py` | `validate_papers()` | Validate with Pydantic |
| Asset 3 | `assets/store.py` | `store_in_cassandra()` | Insert to DB |
| Resource | `resources/cassandra.py` | `cassandra_resource` | DB connection pool |
| Resource | `resources/arxiv.py` | `arxiv_client_resource` | API client |
| Job | `jobs/ingestion_job.py` | `daily_ingestion_job` | 3-asset pipeline |
| Schedule | `jobs/ingestion_job.py` | `daily_ingestion_schedule` | Daily 2 AM UTC |
| Entrypoint | `dagster_pipeline.py` | `defs` | Main Definitions object |
| Config | `config.yaml` | - | Runtime parameters |

---

## Phase 4: Implementation Checklist

- [ ] Copy current code to new structure
- [ ] Create `assets/fetch.py` (wrap PaperFetcher)
- [ ] Create `assets/validate.py` (wrap validate_paper)
- [ ] Create `assets/store.py` (wrap insert_papers)
- [ ] Create `resources/cassandra.py` (connection pool)
- [ ] Create `resources/arxiv.py` (API client resource)
- [ ] Create `jobs/ingestion_job.py` (job + schedule)
- [ ] Create `config.yaml` template
- [ ] Update `dagster_pipeline.py` (main definitions)
- [ ] Test with `dagit -f dagster_pipeline.py`
- [ ] Verify schedule trigger works
- [ ] Deploy to production environment

---

**Next**: Implement Phase 4 using this design blueprint.
