# Dagster Implementation Checklist - Pipelines & Scripts

**Phase 4: Implementation Tasks**

---

## 📁 PIPELINES FOLDER STRUCTURE

Below is what you need to create/modify in the `pipelines/` directory:

```
pipelines/
├── __init__.py                          # ✅ NEW - Package init
├── DESIGN.md                            # ✅ DONE - Design document (reference)
├── config.yaml                          # ✅ DONE - Configuration template
├── dagster_pipeline.py                  # 🔄 MODIFY - Main entry point
│
├── assets/                              # ✅ NEW - Asset definitions
│   ├── __init__.py                      # ✅ NEW - Package init
│   ├── fetch.py                          # ✅ NEW - Asset: fetch_arxiv_papers
│   ├── validate.py                      # ✅ NEW - Asset: validate_papers
│   └── store.py                         # ✅ NEW - Asset: store_in_cassandra
│    
├── resources/                           # ✅ NEW - Resource definitions
│   ├── __init__.py                      # ✅ NEW - Package init
│   ├── cassandra.py                     # ✅ NEW - Cassandra connection pool
│   └── arxiv.py                         # ✅ NEW - ArxivClient wrapper
│
└── jobs/                                # ✅ NEW - Job definitions
    ├── __init__.py                      # ✅ NEW - Package init
    └── ingestion_job.py                 # ✅ NEW - Job + Schedule definition

# Old files (can remove/replace):
# - assets.py (old, will be refactored into assets/fetch.py, etc.)
# - jobs.py (old, will be refactored into jobs/ingestion_job.py)
```

---

## 📋 PIPELINES FOLDER - IMPLEMENTATION TASKS

### **TASK 1: Create Package Init Files**

| File | Status | Action |
|------|--------|--------|
| `pipelines/__init__.py` | ✅ NEW | Create empty init |
| `pipelines/assets/__init__.py` | ✅ NEW | Create empty init |
| `pipelines/resources/__init__.py` | ✅ NEW | Create resource imports |
| `pipelines/jobs/__init__.py` | ✅ NEW | Create empty init |

---

### **TASK 2: Create Assets** (`pipelines/assets/`)

#### **Asset 1: `pipelines/assets/fetch.py`**
```python
# Wraps: ingestion/fetch_papers.py::PaperFetcher
# Responsibilities:
#   - Call PaperFetcher to fetch from 5 arXiv domains
#   - Output: List[Dict] with 13 fields (arxiv_id, title, abstract, ...)
#   - Logging: Papers fetched by category
#   - Error handling: Automated retry via Dagster

# Key points:
#   - Use @asset decorator from dagster
#   - Accept config for batch_size and categories
#   - Return: List[Dict] (raw papers)
#   - No inputs (external API source)
```

**Checklist for fetch.py:**
- [ ] Import @asset, Config, get_dagster_logger from dagster
- [ ] Import PaperFetcher from ingestion.fetch_papers
- [ ] Define FetchArxivConfig (Pydantic config model)
- [ ] Define fetch_arxiv_papers() asset function
- [ ] Log metrics: total papers fetched
- [ ] Handle arXiv API failures gracefully
- [ ] Return List[Dict]

---

#### **Asset 2: `pipelines/assets/validate.py`**
```python
# Wraps: ingestion/validation.py::validate_paper, PaperModel
# Responsibilities:
#   - Receive raw papers from fetch asset
#   - Apply Pydantic schema validation
#   - Drop invalid papers (non-blocking)
#   - Output: List[Dict] (validated papers only)
#   - Logging: Valid/dropped counts, validation errors

# Key points:
#   - Depends on fetch_arxiv_papers asset (dependency injection)
#   - Use PaperModel for validation
#   - Non-blocking: partial success allowed
#   - Return: List[Dict] (subset of input)
```

**Checklist for validate.py:**
- [ ] Import @asset, Config from dagster
- [ ] Import validate_paper, PaperModel from ingestion.validation
- [ ] Define ValidateConfig (Pydantic config model)
- [ ] Define validate_papers() asset function
- [ ] Accept fetch_arxiv_papers as input parameter
- [ ] Log metrics: total, valid, dropped counts
- [ ] Alert if dropout > 15%
- [ ] Return List[Dict]

---

#### **Asset 3: `pipelines/assets/store.py`**
```python
# Wraps: casandra/insert_papers.py::insert_papers
# Responsibilities:
#   - Receive validated papers from validate asset
#   - Insert into Cassandra papers_raw table
#   - Track batch_id for this ingestion run
#   - Output: Dict summary (batch_id, inserted count, etc.)
#   - Logging: Insert metrics, failures

# Key points:
#   - Depends on validate_papers asset (dependency injection)
#   - Depends on cassandra_resource (resource injection)
#   - Idempotent: batch_id tracks each run
#   - Return: Dict with batch_id, inserted, failed counts
```

**Checklist for store.py:**
- [ ] Import @asset, Config from dagster
- [ ] Import insert_papers from casandra.insert_papers
- [ ] Define CassandraConfig (Pydantic config model)
- [ ] Define store_in_cassandra() asset function
- [ ] Accept validate_papers as input parameter
- [ ] Accept cassandra_resource as injected resource
- [ ] Log metrics: batch_id, insert count, failures
- [ ] Return Dict (batch summary)

---

### **TASK 3: Create Resources** (`pipelines/resources/`)

#### **Resource 1: `pipelines/resources/cassandra.py`**
```python
# Wraps: casandra/cassandra_connection.py (or new)
# Responsibilities:
#   - Create reusable Cassandra connection pool
#   - Singleton per pipeline run
#   - Auto-cleanup on run end

# Key points:
#   - @resource decorator
#   - Config: contact_points, keyspace, consistency_level, pool_size, timeout
#   - Yield connection for use in assets
#   - ensure cleanup (shutdown)
```

**Checklist for cassandra.py:**
- [ ] Import @resource, Field from dagster
- [ ] Import Cluster, ConsistencyLevel from cassandra.cluster
- [ ] Define CassandraResource class (wrapper)
- [ ] Define cassandra_resource() resource function
- [ ] Create cluster connection
- [ ] Connect to keyspace
- [ ] Yield resource
- [ ] Ensure cleanup in finally block

---

#### **Resource 2: `pipelines/resources/arxiv.py`**
```python
# Wraps: ingestion/arxiv_client.py::ArxivClient
# Responsibilities:
#   - Create reusable ArxivClient instance
#   - Stateless (no cleanup needed)

# Key points:
#   - @resource decorator
#   - Config: batch_size, timeout, max_retries
#   - Yield client for use in assets
```

**Checklist for arxiv.py:**
- [ ] Import @resource, Field from dagster
- [ ] Import ArxivClient from ingestion.arxiv_client
- [ ] Define arxiv_client_resource() resource function
- [ ] Create ArxivClient with config
- [ ] Yield resource
- [ ] Add logging

---

### **TASK 4: Create Jobs** (`pipelines/jobs/`)

#### **Job Definition: `pipelines/jobs/ingestion_job.py`**
```python
# Responsibilities:
#   - Define the 3-asset pipeline (fetch → validate → store)
#   - Define daily schedule (2:00 AM UTC)
#   - Configure retry policies
#   - Add tags for monitoring

# Key points:
#   - define_asset_job() for 3-asset pipeline
#   - @schedule decorator for daily trigger
#   - cron_schedule = "0 2 * * *" (daily 2 AM)
#   - execution_timezone = "UTC"
```

**Checklist for ingestion_job.py:**
- [ ] Import define_asset_job, schedule from dagster
- [ ] Define daily_ingestion_job (asset job)
- [ ] Select 3 assets: fetch, validate, store
- [ ] Add tags (owner, team, sla)
- [ ] Define daily_ingestion_schedule (schedule)
- [ ] Set cron: "0 2 * * *"
- [ ] Set timezone: "UTC"
- [ ] Add description

---

### **TASK 5: Update Main Entrypoint**

#### **File: `pipelines/dagster_pipeline.py`**
```python
# Responsibilities:
#   - Load all assets from assets/ package
#   - Define all resources
#   - Define all jobs and schedules
#   - Expose defs object to Dagit

# Current state: EMPTY
# Action: Populate with Definitions object

# Example structure:
from dagster import Definitions, load_assets_from_package_module
from pipelines import assets, resources, jobs

all_assets = load_assets_from_package_module(assets)

defs = Definitions(
    assets=all_assets,
    resources={
        "cassandra_resource": resources.cassandra_resource,
        "arxiv_client_resource": resources.arxiv_client_resource,
    },
    jobs=[jobs.daily_ingestion_job],
    schedules=[jobs.daily_ingestion_schedule],
)
```

**Checklist for dagster_pipeline.py:**
- [ ] Import Definitions, load_assets_from_package_module from dagster
- [ ] Import assets, resources, jobs packages
- [ ] Load all assets from assets package
- [ ] Create Definitions object with:
  - [ ] assets=all_assets
  - [ ] resources={cassandra_resource, arxiv_client_resource}
  - [ ] jobs=[]
  - [ ] schedules=[]
- [ ] Export defs

---

### **TASK 6: Old Files** (Optional - Keep or Remove)

| File | Status | Action |
|------|--------|--------|
| `pipelines/assets.py` | 🗑️ OLD | Can remove (content → assets/fetch.py) |
| `pipelines/jobs.py` | 🗑️ OLD | Can remove (content → jobs/ingestion_job.py) |

---

## 📁 SCRIPTS FOLDER STRUCTURE

What you need in `scripts/`:

```
scripts/
├── run_ingestion.sh                     # 🔄 MODIFY - Run ETL pipeline
├── run_pipeline.sh                      # 🔄 MODIFY OR REMOVE - Legacy
└── launch_dagit.sh                      # ✅ NEW - Start Dagit UI
```

---

## 📋 SCRIPTS FOLDER - IMPLEMENTATION TASKS

### **SCRIPT 1: `scripts/launch_dagit.sh`** (NEW)

**Purpose**: Start Dagit UI for local development

```bash
#!/bin/bash
# Launch Dagit web UI for arXiv pipeline

# Set environment
export DAGSTER_HOME=/path/to/.dagster

# Navigate to project root
cd "$(dirname "$0")/.."

# Start Dagit
echo "Starting Dagit UI..."
dagit -f pipelines/dagster_pipeline.py -p 3000

echo "✅ Dagit running at http://localhost:3000"
```

**Checklist:**
- [ ] Create `scripts/launch_dagit.sh`
- [ ] Content: Export DAGSTER_HOME, navigate to project root, run `dagit -f pipelines/dagster_pipeline.py`
- [ ] Make executable: `chmod +x scripts/launch_dagit.sh`
- [ ] Test: Run and visit localhost:3000

---

### **SCRIPT 2: `scripts/run_ingestion.sh`** (MODIFY)

**Purpose**: Execute the Dagster ingestion job locally

**Current version** (if any):
```bash
# Probably runs main.py directly
python main.py
```

**New version** (Dagster):
```bash
#!/bin/bash
# Run arXiv ingestion pipeline via Dagster

# Set environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export DAGSTER_HOME=/path/to/.dagster

# Options
MODE=${1:-"local"}  # "local" or "schedule"

if [ "$MODE" = "local" ]; then
    # Run single job execution locally (no scheduling)
    echo "🚀 Running ingestion job (local mode)..."
    dagster job execute -f pipelines/dagster_pipeline.py -j daily_ingestion_job
    
elif [ "$MODE" = "schedule" ]; then
    # Start daemon for scheduled runs
    echo "📅 Starting Dagster daemon for scheduled runs..."
    dagster-daemon run
    
else
    echo "Usage: $0 [local|schedule]"
    echo "  local   - Run job once immediately"
    echo "  schedule - Start daemon for daily scheduling"
fi
```

**Checklist:**
- [ ] Modify `scripts/run_ingestion.sh` with Dagster command
- [ ] Support two modes: local execution + schedule daemon
- [ ] Add helpful echoes/logging
- [ ] Make executable: `chmod +x scripts/run_ingestion.sh`
- [ ] Test both modes

---

### **SCRIPT 3: `scripts/run_pipeline.sh`** (KEEP OR REMOVE)

**Options:**
1. **Keep & Modify**: Update to call Dagster instead of main.py
2. **Remove**: Clean up if no longer needed

**If keeping:**
```bash
#!/bin/bash
# Convenience script for running entire pipeline

# Step 1: Launch Dagit UI (background)
echo "Starting Dagit UI..."
bash scripts/launch_dagit.sh &
DAGIT_PID=$!

# Step 2: Wait for UI to start
sleep 3

# Step 3: Run ingestion job
echo "Running ingestion job..."
bash scripts/run_ingestion.sh local

# Step 4: Show Dagit URL
echo "✅ Pipeline complete!"
echo "📊 View details at http://localhost:3000"

# Cleanup
kill $DAGIT_PID 2>/dev/null || true
```

**Checklist:**
- [ ] Decide: keep or remove?
- [ ] If keep: update to use new scripts
- [ ] Make executable

---

## 🎯 IMPLEMENTATION PRIORITY

### **Phase 4A: Foundation** (Do first)
1. ✅ Create `pipelines/__init__.py`
2. ✅ Create `pipelines/assets/__init__.py`, `pipelines/resources/__init__.py`, `pipelines/jobs/__init__.py`
3. ✅ Create `pipelines/assets/fetch.py`
4. ✅ Create `pipelines/assets/validate.py`
5. ✅ Create `pipelines/assets/store.py`

### **Phase 4B: Resources & Jobs** (Then)
6. ✅ Create `pipelines/resources/cassandra.py`
7. ✅ Create `pipelines/resources/arxiv.py`
8. ✅ Create `pipelines/jobs/ingestion_job.py`

### **Phase 4C: Integration** (Finally)
9. ✅ Update `pipelines/dagster_pipeline.py`
10. ✅ Create `scripts/launch_dagit.sh`
11. ✅ Modify `scripts/run_ingestion.sh`
12. ✅ Test all pieces together

---

## ✅ VERIFICATION CHECKLIST

After implementation, verify:

```bash
# 1. Check Python syntax
python -m py_compile pipelines/dagster_pipeline.py

# 2. Verify Dagster recognizes assets
dagster job list -f pipelines/dagster_pipeline.py

# 3. Launch Dagit UI
bash scripts/launch_dagit.sh
# Visit http://localhost:3000
# Should show:
# - 3 assets: fetch, validate, store
# - 1 job: daily_ingestion_job
# - 1 schedule: daily_ingestion_schedule

# 4. Test local execution
bash scripts/run_ingestion.sh local
# Should execute pipeline and show results in Dagit

# 5. Verify Cassandra connection
# Check logs for successful Cassandra operations
```

---

## 📊 SUMMARY TABLE

| Folder | File | Action | Purpose |
|--------|------|--------|---------|
| pipelines/ | `__init__.py` | CREATE | Package init |
| pipelines/ | `dagster_pipeline.py` | MODIFY | Main entrypoint |
| pipelines/assets/ | `__init__.py` | CREATE | Package init |
| pipelines/assets/ | `fetch.py` | CREATE | Fetch asset |
| pipelines/assets/ | `validate.py` | CREATE | Validate asset |
| pipelines/assets/ | `store.py` | CREATE | Store asset |
| pipelines/resources/ | `__init__.py` | CREATE | Package init |
| pipelines/resources/ | `cassandra.py` | CREATE | Cassandra resource |
| pipelines/resources/ | `arxiv.py` | CREATE | ArxivClient resource |
| pipelines/jobs/ | `__init__.py` | CREATE | Package init |
| pipelines/jobs/ | `ingestion_job.py` | CREATE | Job + Schedule |
| pipelines/ | `config.yaml` | DONE ✅ | Configuration |
| scripts/ | `launch_dagit.sh` | CREATE | Start UI |
| scripts/ | `run_ingestion.sh` | MODIFY | Run job |

---

**Total:** 17 tasks
- **9 CREATE** new files
- **2 MODIFY** existing files
- **1 VERIFY** config.yaml

Ready to start implementation? I can help you create these files!
