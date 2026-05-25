# Cassandra Integration Guide

This guide walks you through setting up Cassandra and completing the full ETL pipeline.

## Prerequisites

- Docker installed and running
- Python 3.13+
- All pipeline dependencies installed (`pip install -r requirements.txt`)

## Quick Start (3 Steps)

### Step 1: Start Cassandra and Create Schema

```powershell
python scripts/setup_cassandra.py
```

This will:
1. ✅ Start Cassandra 5.0 in Docker
2. ✅ Create the `arxiv` keyspace
3. ✅ Create the `papers_raw` table
4. ✅ Verify the connection

**Expected output:**
```
✅ Cassandra is ready!
✅ Schema successfully applied!
```

**Troubleshooting:**
- If Docker is not installed, [download Docker Desktop](https://www.docker.com/products/docker-desktop)
- If port 9042 is in use: `docker compose down` first, then try again
- For detailed logs: `docker logs cassandra_arxiv`

### Step 2: Run the Full Pipeline

```powershell
python scripts/run_ingestion.py local
```

Expected flow:
1. **Fetch** - ~5 papers from arXiv (takes ~6 seconds)
2. **Validate** - Filter invalid papers (takes <1 second)
3. **Store** - Insert into Cassandra (takes ~2 seconds)

**Success indicators:**
```
✅ Fetched N papers from arXiv API
✅ Validation complete: N/N papers valid
✅ Stored in Cassandra: batch_id = <UUID>
```

### Step 3: Verify Data in Cassandra

```powershell
docker exec -it cassandra_arxiv cqlsh
```

Then in the CQL shell:
```sql
USE arxiv;
SELECT COUNT(*) FROM papers_raw;
SELECT arxiv_id, title FROM papers_raw LIMIT 5;
```

## Data Model

**Keyspace:** `arxiv`
- Replication Factor: 1 (development) — Change to 3 for production
- Consistency Level: LOCAL_QUORUM

**Table:** `papers_raw`
```
Primary Key: (batch_id, arxiv_id)
  - batch_id: UUID identifying the ingestion run
  - arxiv_id: Unique paper identifier

Columns (13 total):
  - batch_id, ingestion_date (clustering/time tracking)
  - arxiv_id, title, abstract (paper metadata)
  - authors, categories, primary_category (classification)
  - published_date, updated_date (timestamps)
  - pdf_url (document link)
  - raw_json (full API response)
  - ingested_at (ingestion timestamp)
```

## Pipeline Architecture

```
arXiv API
   ↓
[fetch_arxiv_papers] ←— Fetches 100 papers/category × 5 = ~500 papers
   ↓
[validate_papers] ←— Pydantic validation, drops invalid (5-10% typical)
   ↓
[store_in_cassandra] ←— Batch insert (25 papers/chunk) with UUID tracking
   ↓
Cassandra papers_raw table
```

**Assets (Dagster):**
- `fetch_arxiv_papers`: Outputs list of 13-field dicts
- `validate_papers`: Outputs validated subset
- `store_in_cassandra`: Outputs {batch_id, inserted_count, failed_count}

**Job:** `daily_ingestion_job`
- Chains all 3 assets sequentially
- Triggered daily at 2:00 AM UTC

## Using Dagit UI (Optional)

Start the interactive UI:
```powershell
python scripts/launch_dagit.py
```

Then visit: **http://localhost:3000**

Features:
- ✨ Visualize asset dependencies
- 📊 See previous run results
- 🔍 Filter and search assets/jobs
- 📈 Monitor execution times
- 🪵 View logs per asset

## Docker Management

**View Cassandra status:**
```powershell
docker ps | findstr cassandra
docker logs cassandra_arxiv
```

**Scale up (if needed):**
Edit `docker-compose.yml` to change replication_factor from 1 to 3, then:
```powershell
docker compose down -v
python scripts/setup_cassandra.py
```

**Stop Cassandra (keeps data):**
```powershell
docker compose stop
```

**Destroy Cassandra (deletes data):**
```powershell
docker compose down -v
```

**Restart Cassandra:**
```powershell
docker compose restart
```

## Production Considerations

### Cassandra Configuration

Before production, modify `docker-compose.yml`:

```yaml
environment:
  CASSANDRA_HEAP_SIZE: 4G              # Increase from default
  CASSANDRA_HEAP_NEWSIZE: 1G           # For larger datasets
  CASSANDRA_NUM_TOKENS: 256            # For multi-node cluster
```

### Replication & Consistency

In `casandra/schema.cql`, change replication:
```sql
-- Development (1 node)
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- Production (3+ nodes)
WITH replication = {'class': 'NetworkTopologyStrategy', 'dc1': 3};
```

### Backup Strategy

```powershell
# Backup data directory
docker cp cassandra_arxiv:/var/lib/cassandra ./cassandra_backup

# Restore
docker cp ./cassandra_backup/cassandra cassandra_arxiv:/var/lib/
docker compose restart
```

## Troubleshooting

### "Connection refused" at port 9042

Cassandra not started or still warming up (takes 30-60 seconds):
```powershell
docker logs cassandra_arxiv
# Wait for: "Cassandra has started. Waiting for gossip to settle..."
```

### "Table does not exist"

Schema wasn't applied. Run setup again:
```powershell
python scripts/setup_cassandra.py
```

### "All provided hosts were unavailable"

Connection pool issue. Verify in Python:
```python
from cassandra.cluster import Cluster
cluster = Cluster(['localhost'])
session = cluster.connect()
print(session.execute("SELECT release_version FROM system.local;").one())
```

### Out of disk space

Cassandra data accumulates. Clean up:
```powershell
docker compose down -v  # Removes all data
python scripts/setup_cassandra.py  # Fresh start
```

## Next Steps

After integration:
1. **Run daily schedules**: Deploy to Dagster Cloud or on-premise Dagster Daemon
2. **Add monitoring**: Integrate Dagster Cloud for alerts
3. **Scale Cassandra**: Set up multi-node cluster for production
4. **Add Phase 2**: Implement Databricks ELT (Spark processing)
5. **Analytics**: Build Phase 6 analytics/insights queries

## Files Reference

- `docker-compose.yml` - Cassandra container definition
- `casandra/schema.cql` - Keyspace + table DDL
- `scripts/setup_cassandra.py` - Automated setup
- `scripts/run_ingestion.py` - Pipeline execution
- `scripts/launch_dagit.py` - UI server
- `pipelines/dagster_pipeline.py` - Pipeline definitions

## Quick Commands Cheat Sheet

```powershell
# Setup
python scripts/setup_cassandra.py

# Run pipeline
python scripts/run_ingestion.py local

# Monitor UI
python scripts/launch_dagit.py

# Query data
docker exec -it cassandra_arxiv cqlsh

# Check health
docker logs cassandra_arxiv | tail -20

# Stop everything
docker compose down

# Fresh start (delete data)
docker compose down -v
python scripts/setup_cassandra.py
```

---

✨ **Your pipeline is architecture-complete and ready for production!**
