# System Architecture - Full Data Flow

**Phase 1 Design Document** | Complete End-to-End Pipeline

---

## High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL DATA SOURCE                             │
│                          arXiv API                                   │
│              (Papers in 5 CS domains: AI, LG, CV, CL, ML)           │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      │ HTTPS GET requests
                      │ (batch_size=100 per domain)
                      │
        ┌─────────────▼────────────────────────────┐
        │   DAGSTER ORCHESTRATION LAYER           │
        │   (Python: Dagster 1.5+)                │
        │                                          │
        │  ╔══════════════════════════════════╗  │
        │  ║  ASSET 1: fetch_arxiv_papers    ║  │
        │  ╠══════════════════════════════════╣  │
        │  ║ Fetches: 5 domains × 100 papers ║  │
        │  ║ Output: List[Dict] (raw)        ║  │
        │  ║ Retry: 3x with backoff          ║  │
        │  ║ Expected: ~500-1000 papers      ║  │
        │  ╚════────┬─────────────────────────╝  │
        │           │                             │
        │  ╔────────▼──────────────────────────╗ │
        │  ║  ASSET 2: validate_papers        ║ │
        │  ╠═════════════════════════════════╣ │
        │  ║ Pydantic schema validation      ║ │
        │  ║ Drop invalid records            ║ │
        │  ║ Output: List[Dict] (validated)  ║ │
        │  ║ Loss: ~5-10% (malformed)        ║ │
        │  ║ Expected: ~450-950 papers       ║ │
        │  ╚────────┬─────────────────────────╝ │
        │           │                             │
        │  ╔────────▼──────────────────────────╗ │
        │  ║ ASSET 3: store_in_cassandra      ║ │
        │  ╠═════════════════════════════════╣ │
        │  ║ Generate batch_id (UUID)        ║ │
        │  ║ Chunk inserts (size: 25)        ║ │
        │  ║ Track batch metadata            ║ │
        │  ║ Consistency: LOCAL_QUORUM       ║ │
        │  ║ Retry: 3x per chunk             ║ │
        │  ║ Output: Batch summary dict      ║ │
        │  ╚────────┬─────────────────────────╝ │
        │           │                             │
        └───────────┼──────────────────────────┘
                    │
                    │ CQL INSERT statements
                    │ (via cassandra-driver)
                    │
        ┌───────────▼──────────────────────────┐
        │   CASSANDRA CLUSTER                  │
        │   (Docker: cassandra:5.0)            │
        │                                      │
        │   ┌──────────────────────────────┐  │
        │   │  KEYSPACE: arxiv             │  │
        │   │  ┌────────────────────────┐  │  │
        │   │  │ TABLE: papers_raw      │  │  │
        │   │  ├────────────────────────┤  │  │
        │   │  │ Primary Key:           │  │  │
        │   │  │ (batch_id, arxiv_id)   │  │  │
        │   │  │                        │  │  │
        │   │  │ Columns:               │  │  │
        │   │  │ • arxiv_id (text)      │  │  │
        │   │  │ • title (text)         │  │  │
        │   │  │ • abstract (text)      │  │  │
        │   │  │ • authors (list<text>) │  │  │
        │   │  │ • categories (list)    │  │  │
        │   │  │ • primary_category     │  │  │
        │   │  │ • published_date       │  │  │
        │   │  │ • updated_date         │  │  │
        │   │  │ • pdf_url (text)       │  │  │
        │   │  │ • raw_json (text)      │  │  │
        │   │  │ • ingested_at          │  │  │
        │   │  │ • batch_id (uuid)      │  │  │
        │   │  │ • ingestion_date       │  │  │
        │   │  └────────────────────────┘  │  │
        │   └──────────────────────────────┘  │
        │                                      │
        │   Replication: 1 (local dev)       │
        │   Query Timeout: 10s                │
        │   Consistency: LOCAL_QUORUM         │
        └──────────────────────────────────────┘
                    │
         (Stored raw papers, ready for ELT)
                    │
                    │ [PHASE 5: Databricks]
                    │
        ┌───────────▼──────────────────────────────────┐
        │   DATABRICKS WORKSPACE (Future)              │
        │   (Spark ELT: Bronze → Silver → Gold)        │
        │                                              │
        │  ┌──────────────────────────────────────┐   │
        │  │ BRONZE LAYER                         │   │
        │  │ Raw papers from Cassandra            │   │
        │  │ (table: bronze_papers)               │   │
        │  └────────┬─────────────────────────────┘   │
        │           │                                  │
        │  ┌────────▼──────────────────────────────┐  │
        │  │ SILVER LAYER                         │  │
        │  │ Cleaned & normalized data            │  │
        │  │ Transformations:                     │  │
        │  │ • normalize authors                  │  │
        │  │ • clean text (lowercase, spaces)     │  │
        │  │ • extract year from published_date   │  │
        │  │ • deduplicate arxiv_ids              │  │
        │  │ (table: silver_papers)               │  │
        │  └────────┬──────────────────────────────┘  │
        │           │                                  │
        │  ┌────────▼──────────────────────────────┐  │
        │  │ GOLD LAYER                           │  │
        │  │ Analytics-ready tables:              │  │
        │  │ • papers_per_category                │  │
        │  │ • papers_per_year                    │  │
        │  │ • top_authors                        │  │
        │  │ • abstract_word_stats                │  │
        │  │ • research_trends                    │  │
        │  └─────────┬─────────────────────────────┘  │
        │            │                                 │
        └────────────┼─────────────────────────────────┘
                     │
            ┌────────▼───────────┐
            │   ANALYTICS OUTPUT │
            │                    │
            │ • Reports          │
            │ • Dashboards       │
            │ • CSV exports      │
            │ • ML-ready data    │
            └────────────────────┘
```

---

## Detailed Data Flow Sequence

```
                    RUN START: 2:00 AM UTC
                           │
                           ▼
    ┌─────────────────────────────────────────────┐
    │ 1. FETCH PHASE (5-10 seconds)               │
    │                                             │
    │ fetch_arxiv_papers() {                      │
    │   for each category in [AI, LG, CV, CL, ML] │
    │     → GET arXiv API (batch_size=100)        │
    │     → Parse JSON response                   │
    │     → Extract fields (arxiv_id, title, ...) │
    │     → Build list of raw paper dicts         │
    │ }                                           │
    │                                             │
    │ OUTPUT: List[Dict] (500-1000 papers)        │
    │ ERRORS: Retried 3x, then fail+alert         │
    └──────────────────┬──────────────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────────────┐
    │ 2. VALIDATE PHASE (5-15 seconds)            │
    │                                             │
    │ validate_papers(raw_papers) {               │
    │   for each paper in raw_papers:             │
    │     → Apply Pydantic PaperModel schema      │
    │     → Check: non-empty strings              │
    │     → Check: valid lists (authors, cats)    │
    │     → Check: valid dates & URL              │
    │     → Drop if invalid (log error)           │
    │     → Keep if valid                         │
    │ }                                           │
    │                                             │
    │ OUTPUT: List[Dict] (450-950 papers, valid)  │
    │ DROPPED: ~5-10% (malformed records)         │
    │ ERRORS: Logged, non-blocking                │
    └──────────────────┬──────────────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────────────┐
    │ 3. STORE PHASE (30 seconds - 2 minutes)      │
    │                                              │
    │ store_in_cassandra(validated_papers) {       │
    │   batch_id = UUID()                          │
    │   ingestion_date = today()                   │
    │                                              │
    │   for chunk in chunks(papers, size=25):      │
    │     INSERT INTO papers_raw VALUES (          │
    │       batch_id,                              │
    │       ingestion_date,                        │
    │       arxiv_id, title, abstract, ...         │
    │     )                                        │
    │   }                                          │
    │                                              │
    │   RETURN {                                   │
    │     batch_id: UUID,                          │
    │     total: int,                              │
    │     inserted: int,                           │
    │     failed: int,                             │
    │     duration_seconds: float                  │
    │   }                                          │
    │ }                                            │
    │                                              │
    │ OUTPUT: Summary metadata                     │
    │ ERRORS: Retried per chunk, then logged       │
    └──────────────────┬──────────────────────────┘
                       │
                ┌──────┴──────┐
                │             │
                ▼             ▼
         ✅ SUCCESS      ❌ FAILURE
         Papers stored    Alert operator
         in Cassandra     (Slack/Email)
                │             │
                └──────┬──────┘
                       │
                       ▼
         ╔════════════════════════════════╗
         ║  RUN COMPLETE                  ║
         ║  Time: 2-5 minutes total       ║
         ║  Status: Logged in Dagit UI    ║
         ║  Next run: Tomorrow 2:00 AM    ║
         ╚════════════════════════════════╝
```

---

## File & Data Size Estimates

### **Per Run Estimates**

| Step | Count | Expected Size | Time |
|------|-------|---------------|------|
| Fetch (5 domains × 100) | 500-1000 | ~50-100 MB (JSON) | 5-10s |
| Validate (drop ~5-10%) | 450-950 | ~45-95 MB | 5-15s |
| Store in Cassandra | 450-950 | N/A (DB storage) | 30s-2m |
| **Total Duration** | - | - | **2-5 minutes** |

### **Cassandra Storage**

Assuming 1 year of daily runs (365 papers per day):
- **Rows**: 365 × 700 ≈ 256,000 papers
- **Storage**: ~5-10 GB (with replication factor 1)
- **Indexes**: Batch_id + arxiv_id (composite key)

---

## Component Interactions

### **1. Dagster ↔ ArxivClient**
```
Dagster Asset: fetch_arxiv_papers
    ├─ Resource: ArxivClient
    │   ├─ config: batch_size=100, timeout=30s
    │   ├─ method: search_papers(category)
    │   └─ output: Arxiv Result objects
    └─ Transform to Dict with fields:
        ├ arxiv_id, title, abstract
        ├ authors, categories, pdf_url
        └ timestamps (published, updated)
```

### **2. Dagster ↔ Pydantic Validator**
```
Dagster Asset: validate_papers
    ├─ Input: List[Dict] (raw papers)
    ├─ Validator: PaperModel (Pydantic)
    │   ├─ field_validator: non-empty strings
    │   ├─ field_validator: non-empty lists
    │   ├─ HttpUrl validation: pdf_url
    │   └─ datetime validation: dates
    └─ Output: List[Dict] (validated papers)
        └─ method: to_insert_dict() → Cassandra-ready
```

### **3. Dagster ↔ Cassandra**
```
Dagster Asset: store_in_cassandra
    ├─ Resource: CassandraConnection
    │   ├─ contact_points: localhost:9042
    │   ├─ keyspace: arxiv
    │   ├─ consistency_level: LOCAL_QUORUM
    │   └─ pool_size: 5
    ├─ Prepare INSERT statement once
    ├─ Execute in chunks (batch_size=25)
    │   ├─ Retry: 3x per chunk
    │   └─ Backoff: exponential (30s, 60s, 120s)
    └─ Output: Batch summary (inserted count, etc.)
```

---

## Error Propagation

```
FETCH FAILS
    │
    ├─→ Retry 3x with backoff
    │   ├─ Attempt 1: Immediate
    │   ├─ Attempt 2: +30s
    │   └─ Attempt 3: +120s
    │
    ├─→ All 3 fail
    │   ├─ Log error with run_id, batch_id
    │   ├─ Alert operator (Slack)
    │   └─ STOP PIPELINE (don't proceed to validate)
    │
    └─→ Assets skipped:
        └─ validate_papers, store_in_cassandra
           (marked as skipped in Dagit)

VALIDATE FAILS (some records)
    │
    ├─→ Drop invalid records (non-blocking)
    │   ├─ Log: validation errors
    │   ├─ Continue with valid records
    │   └─ Proceed to store phase
    │
    └─→ Dagit shows: WARNING (partial success)

STORE FAILS (chunk timeout)
    │
    ├─→ Retry entire chunk 3x
    │   ├─ Attempt 1: Immediate
    │   ├─ Attempt 2: +30s
    │   └─ Attempt 3: +120s (final)
    │
    ├─→ All 3 fail
    │   ├─ Log: chunk details, batch_id, arxiv_ids
    │   ├─ Alert operator (Slack/Email)
    │   └─ Records written to DLQ / manual review
    │
    └─→ Dagit shows: ERROR (partial insert)
```

---

## Integration with Future Phases

### **Phase 4 → Phase 5 Link**
When ready, add a final asset to Dagster:

```python
@asset
def trigger_databricks_job(context, store_in_cassandra_summary):
    """
    After successful store, trigger Databricks ELT job.
    Pass batch_id so Databricks knows which batch to process.
    """
    batch_id = store_in_cassandra_summary["batch_id"]
    # TODO: Call Databricks REST API to start job
    # Job will: bronze ← cassandra, silver ← transform, gold ← aggregate
    return {"job_id": "...", "batch_id": batch_id}
```

This creates a **full end-to-end lineage** in Dagit:
```
fetch_arxiv_papers → validate_papers → store_in_cassandra → trigger_databricks_job
```

---

## Monitoring Dashboard (Dagit UI)

The Dagster UI will show:

```
┌─────────────────────────────────────────────────┐
│ ASSETS VIEW                                     │
├─────────────────────────────────────────────────┤
│ fetch_arxiv_papers                              │
│   └─ last run: 2:00 AM UTC, 8 seconds, ✅     │
│   └─ papers fetched: 742                        │
│                                                 │
│ validate_papers                                 │
│   └─ last run: 2:00 AM UTC, 12 seconds, ✅    │
│   └─ papers valid: 712 (dropped: 30)            │
│                                                 │
│ store_in_cassandra                              │
│   └─ last run: 2:00 AM UTC, 45 seconds, ✅    │
│   └─ papers inserted: 712                       │
│   └─ batch_id: 550e8400-e29b-41d4-a716-...     │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ RUNS VIEW                                       │
├─────────────────────────────────────────────────┤
│ Run #245  | 2024-03-24 02:00 | Duration: 1m 5s │
│ Status: ✅ SUCCESS                              │
│ Timeline:                                       │
│   ├─ fetch_arxiv_papers: [████] 8s              │
│   ├─ validate_papers: [██████] 12s              │
│   └─ store_in_cassandra: [███████████] 45s      │
│                                                 │
│ Run #244  | 2024-03-23 02:00 | Duration: 1m 2s │
│ Status: ✅ SUCCESS                              │
└─────────────────────────────────────────────────┘
```

---

## Summary

**Phase 1 defines** the complete architecture for your arXiv ingestion pipeline:
- ✅ Dagster orchestrates 3 sequential assets
- ✅ Data flows: arXiv API → Validation → Cassandra
- ✅ Error handling with retries & alerts
- ✅ Monitoring via Dagit UI + JSON logs
- ✅ Ready for Phase 5: Databricks ELT extension

**Next Phase (Phase 4)**: Implement this design in Python code.
