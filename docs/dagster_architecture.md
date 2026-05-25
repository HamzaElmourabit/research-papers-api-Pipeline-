# Dagster Orchestration Layer - Architecture Design

**Phase 1 Design Document** | Status: Design Phase

---

## Overview

Dagster serves as the **orchestration and scheduling layer** for the arXiv research papers ETL pipeline. It coordinates three core operations:
1. Fetching papers from arXiv API
2. Validating paper metadata
3. Storing validated papers in Cassandra

---

## Dagster Responsibilities

### 1. **Scheduling & Triggering**
- **Frequency**: Daily ETL runs at 2:00 AM UTC
- **Backfill Capability**: Manually trigger historical data ingestion (e.g., fetch last 30 days)
- **Manual Triggers**: On-demand pipeline runs for testing/validation
- **Timeout**: 30 minutes max execution time per run

### 2. **Pipeline Orchestration**
The pipeline consists of **three assets** (data products) executed in sequence:

#### **Asset 1: `fetch_arxiv_papers`**
- **Input**: None (external data source)
- **Output**: List of raw paper dictionaries from arXiv
- **Action**: 
  - Fetches papers from 5 CS domains (cs.AI, cs.LG, cs.CV, cs.CL, stat.ML)
  - Batch size: 100 papers per category
  - Total expected: ~500-1000 papers per run
- **Error Handling**: 
  - Retry: 3 attempts with exponential backoff (30s, 60s, 120s)
  - Failure Action: Log error, alert operator, skip this domain
- **Idempotency**: None (API responses are different each time)
- **Output Schema**:
  ```python
  {
    "arxiv_id": str,
    "title": str,
    "abstract": str,
    "authors": List[str],
    "categories": List[str],
    "primary_category": str,
    "published_date": datetime,
    "updated_date": datetime,
    "pdf_url": str,
    "raw_json": str,
    "ingested_at": datetime
  }
  ```

#### **Asset 2: `validate_papers`**
- **Input**: Raw papers from `fetch_arxiv_papers`
- **Output**: List of validated paper dictionaries
- **Action**:
  - Apply Pydantic schema validation
  - Check non-empty fields (arxiv_id, title, abstract, primary_category)
  - Verify author and category lists are non-empty
  - Validate PDF URL format
- **Error Handling**:
  - Drop invalid records silently
  - Log validation failures (schema errors, missing fields)
  - Allow partial success (some papers pass, others fail)
- **Expected Loss**: ~5-10% of raw papers (malformed records)
- **Output**: List of validated dicts, ready for Cassandra insertion

#### **Asset 3: `store_in_cassandra`**
- **Input**: Validated papers from `validate_papers`
- **Output**: Insertion summary metadata
- **Action**:
  - Generate batch_id (UUID) for this ingestion run
  - Insert papers into `papers_raw` table in chunks (size: 25)
  - Track ingestion_date and timestamp
  - Handle duplicate arxiv_ids gracefully (update or skip)
- **Error Handling**:
  - Chunk failures: Retry entire chunk (3 times)
  - Connection failures: Retry with backoff
  - After 3 retries: Log batch_id for manual review
- **Idempotency**: Batch ID ensures run tracking; same batch_id = same ingestion run
- **Consistency Level**: LOCAL_QUORUM (strong consistency for critical data)
- **Output**:
  ```python
  {
    "batch_id": UUID,
    "total": int,
    "inserted": int,
    "failed": int,
    "ingestion_date": datetime,
    "duration_seconds": float
  }
  ```

---

## Resource Dependencies

### **Cassandra Resource**
- **Pool**: Reusable connection pool (singleton per run)
- **Config Parameters**:
  - `contact_points`: ['localhost:9042']
  - `keyspace`: 'arxiv'
  - `consistency_level`: ConsistencyLevel.LOCAL_QUORUM
  - `timeout`: 10 seconds per query
  - `pool_size`: 5 connections
- **Cleanup**: Auto-close session after pipeline completes

### **ArxivClient Resource**
- **Type**: Reusable API client wrapper
- **Config Parameters**:
  - `batch_size`: 100 papers per request
  - `timeout`: 30 seconds per API call
  - `retry_count`: 3
  - `backoff_factor`: 2 (exponential)
- **Cleanup**: None required (stateless)

---

## Error Handling Strategy

### **Retry Policy**
- **Max Retries**: 3 attempts
- **Backoff**: Exponential (base: 1s)
  - Attempt 1: Immediate
  - Attempt 2: After 30 seconds
  - Attempt 3: After 120 seconds
  - Final Failure: Stop pipeline, alert

### **Failure Scenarios**

| Scenario | Asset | Action |
|----------|-------|--------|
| API timeout | fetch_arxiv_papers | Retry 3x, then fail |
| Invalid paper schema | validate_papers | Log & skip (continue) |
| Cassandra down | store_in_cassandra | Retry 3x, then fail |
| Network partition | Any | Retry 3x, then fail |
| Partial batch failure | store_in_cassandra | Log failed chunk, notify ops |

### **Dead Letter Handling**
- Failed papers logged to: `logs/failed_papers_{batch_id}.json`
- Failed batches logged with batch_id for re-processing
- Operator notified via Slack/Email on pipeline failure

---

## Monitoring & Observability

### **Dagit UI**
- **Real-time Dashboard**: View pipeline runs, execution duration, asset lineage
- **Run History**: Track all historical runs with status
- **Logs**: Structured JSON logs searchable by batch_id, run_id

### **Metrics to Track**
- **fetch_arxiv_papers**:
  - Papers fetched by category
  - API response time
  - Failures/retries
  
- **validate_papers**:
  - Papers validated (successful)
  - Papers dropped (failed validation)
  - Validation error breakdown
  
- **store_in_cassandra**:
  - Papers inserted into DB
  - Papers failed to insert
  - Batch insertion time
  - Cassandra query latency

### **Alerting**
- **Slack Notification**: On pipeline failure or manual trigger
- **Email**: Daily summary (# papers fetched, validated, stored)
- **Threshold Alerts**:
  - If dropped papers > 15%: Alert ops
  - If insertion latency > 5 minutes: Alert ops
  - If API timeout > 2x per run: Alert ops

### **Logging Strategy**
- **Format**: JSON structured logs
- **Fields**: timestamp, run_id, batch_id, asset, level, message
- **Storage**: File-based (logs/) + optional cloud logging (GCP Stackdriver, etc.)
- **Retention**: 30 days

---

## Data Quality Checks

### **Pre-Insertion Validation** (Asset 2)
- ✅ Non-empty strings: arxiv_id, title, abstract, primary_category
- ✅ Non-empty lists: authors (≥1 element), categories (≥1 element)
- ✅ Valid datetime: published_date, updated_date
- ✅ Valid URL: pdf_url (HttpUrl format)
- ❌ Drop if any validation fails

### **Post-Insertion Verification** (Asset 3)
- ✅ Row count matches expected inserts
- ✅ Batch_id consistent across all rows
- ✅ No duplicate arxiv_ids within same batch (detect via count query)

### **Freshness SLA**
- **Target**: Papers available in Cassandra within 1 hour of fetch
- **Actual**: 2-5 minutes (fetch + validate + store)

---

## Integration Points

### **Upstream: arXiv API**
- **Contract**: Returns JSON with paper metadata
- **Failure Mode**: HTTP 429 (rate limit), 500 (server error), timeout
- **Resilience**: Exponential backoff, max 3 retries

### **Downstream: Cassandra**
- **Contract**: Insert INTO papers_raw (batch_id, fields...)
- **Failure Mode**: Connection refused, query timeout, write failure
- **Resilience**: Connection pooling, exponential backoff, batch retries

### **Future: Databricks (Phase 5)**
- **Integration**: Trigger Spark job after successful Cassandra insertion
- **Data Transfer**: Cassandra → Databricks reads papers_raw
- **Schema**: Same 13 columns + additional spark-generated metadata

---

## Configuration & Customization

### **Environment Variables**
```bash
# Cassandra
CASSANDRA_HOSTS=localhost:9042
CASSANDRA_KEYSPACE=arxiv
CASSANDRA_CONSISTENCY_LEVEL=LOCAL_QUORUM

# ArxivClient
ARXIV_BATCH_SIZE=100
ARXIV_TIMEOUT=30
ARXIV_CATEGORIES=cs.AI,cs.LG,cs.CV,cs.CL,stat.ML

# Dagster
DAGSTER_HOME=/path/to/dagster/storage
DAGSTER_LOG_LEVEL=INFO
```

### **Runtime Parameters** (via config.yaml)
- Batch sizes (fetch, insert)
- Retry counts and backoff factors
- Timeout thresholds
- Notification channels (Slack / Email)

---

## Phase 4: Implementation Roadmap

When you're ready to implement (Phase 4), you'll create:

1. **`pipelines/assets/fetch.py`** - `fetch_arxiv_papers` asset
2. **`pipelines/assets/validate.py`** - `validate_papers` asset
3. **`pipelines/assets/store.py`** - `store_in_cassandra` asset
4. **`pipelines/resources/`** - Cassandra & ArxivClient resources
5. **`pipelines/dagster_pipeline.py`** - Job definition & scheduling
6. **`pipelines/config.yaml`** - Runtime configuration

---

## Summary

| Aspect | Details |
|--------|---------|
| **Frequency** | Daily at 2:00 AM UTC |
| **Duration** | 2-5 minutes per run |
| **Papers/Run** | 500-1000 raw, 450-950 valid inserted |
| **Failure Tolerance** | 3 retries per asset, alerts on final failure |
| **Data Quality** | Pydantic validation, schema enforcement |
| **Monitoring** | Dagit UI + Slack/Email alerts |
| **Idempotency** | Batch ID tracking per run |

---

**Next Step**: Create [pipelines/DESIGN.md](pipelines/DESIGN.md) for code structure planning.
