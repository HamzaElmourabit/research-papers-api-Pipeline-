# 🎯 GitHub Actions Quick Reference

## 📋 CI/CD Pipeline Overview

**Location:** `.github/workflows/ci-cd.yml` (already configured)

**Triggered by:**
- ✅ Push to `main` or `develop` branches
- ✅ Pull requests to `main` or `develop`
- ✅ Daily schedule @ 2 AM UTC

**Total Runtime:** ~20-30 minutes first run, ~15-20 minutes subsequent runs

---

## 🔄 7-Stage Pipeline Details

### Stage 1️⃣: Code Quality Checks
**Duration:** 2-3 minutes

```yaml
name: code-quality
runs-on: ubuntu-latest

checks:
  - Black formatter check (code formatting)
  - isort import ordering check
  - Flake8 linting (PEP 8 compliance)
  - mypy type checking (optional)
```

**What it validates:**
- ✅ All Python files follow Black formatting
- ✅ Imports are organized with isort
- ✅ No PEP 8 violations detected
- ✅ Type hints are valid

**Failure reasons:**
- ❌ Code not formatted with Black
- ❌ Import order incorrect
- ❌ PEP 8 violations
- ❌ Type hint errors

**Fix:**
```bash
black .
isort .
flake8 . --statistics
mypy . --ignore-missing-imports
```

---

### Stage 2️⃣: Security Scan
**Duration:** 3-5 minutes

```yaml
name: security
runs-on: ubuntu-latest

tools:
  - Trivy (vulnerability scanner)
  - Safety (dependency checker)
  - GitHub CodeQL (code analysis)
```

**What it validates:**
- ✅ No critical vulnerabilities in dependencies
- ✅ No known CVEs in packages
- ✅ Code security issues identified

**Outputs:**
- SARIF report → GitHub Security tab
- JSON report → Available in logs
- Summary → Workflow summary

**Fix:**
```bash
pip install safety
safety check
pip list --outdated
pip install --upgrade vulnerable-package
```

---

### Stage 3️⃣: Unit Tests
**Duration:** 2-3 minutes

```yaml
name: unit-tests
runs-on: ubuntu-latest

services:
  cassandra:
    image: cassandra:5.0
    port: 9042

test-framework: pytest
coverage-target: >80%
```

**What it validates:**
- ✅ All pytest tests pass
- ✅ Code coverage >80%
- ✅ No import errors
- ✅ Module initialization works

**Files tested:**
- `tests/test_improvements.py`
- `tests/test_kafka_flow.py`
- `ingestion/` module tests
- `pipelines/` module tests

**Outputs:**
- Coverage report (HTML)
- Coverage report (XML for Codecov)
- Test summary
- Uploaded to Codecov

**Fix if failing:**
```bash
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html to see coverage
```

---

### Stage 4️⃣: Integration Tests
**Duration:** 3-5 minutes

```yaml
name: integration-tests
depends: unit-tests
runs-on: ubuntu-latest

services:
  cassandra:
    image: cassandra:5.0
    port: 9042
  kafka:
    image: kafka:7.5.0
    port: 9092
  postgres:
    image: postgres:15
    port: 5432
```

**What it validates:**
- ✅ Full ETL pipeline executes
- ✅ Cassandra connection works
- ✅ Kafka message flow works
- ✅ Database operations succeed
- ✅ End-to-end data flow functional

**Test scenarios:**
- Fetch papers from arXiv API
- Validate paper schema
- Insert into Cassandra
- Query results
- Export to Parquet

**Fix if failing:**
```bash
# Run locally with docker-compose
docker-compose up -d
python scripts/test_pipeline.py
docker-compose logs cassandra
```

---

### Stage 5️⃣: Docker Build
**Duration:** 5-10 minutes

```yaml
name: docker-build
depends: integration-tests
runs-on: ubuntu-latest

registry: ghcr.io

build-context:
  - Dockerfile (multi-stage)
  - requirements.txt
  - All source code

push-to: GitHub Container Registry (GHCR)
tag-as: 
  - ghcr.io/USERNAME/research-papers-pipeline:latest
  - ghcr.io/USERNAME/research-papers-pipeline:v1.0.0
```

**What it builds:**
- ✅ Multi-stage Docker image
- ✅ Python 3.13 runtime
- ✅ All dependencies installed
- ✅ Security scanning included

**Output:**
- Docker image pushed to GHCR
- Available at: `ghcr.io/USERNAME/research-papers-pipeline:latest`

**Access image:**
```bash
# List images
gh api user/packages --jq '.[] | .name'

# Pull image
docker pull ghcr.io/USERNAME/research-papers-pipeline:latest

# Run image
docker run -d \
  --name arxiv-pipeline \
  --network arxiv_network \
  ghcr.io/USERNAME/research-papers-pipeline:latest
```

**Fix if failing:**
```bash
# Test locally
docker build -t arxiv-pipeline:test .
docker run arxiv-pipeline:test python -m pytest tests/

# Check for build errors
docker build -t arxiv-pipeline:test . --progress=plain
```

---

### Stage 6️⃣: Performance Tests
**Duration:** 2-3 minutes

```yaml
name: performance
runs-on: ubuntu-latest

benchmarks:
  - ETL execution time
  - Memory usage
  - API response time
  - Database query performance
```

**What it measures:**
- ✅ ETL completes in <1 minute
- ✅ Memory usage <1GB
- ✅ API calls <5 seconds
- ✅ Database queries <500ms

**Report:**
- Comparison with baseline
- Performance trends
- Warnings on degradation

**Fix if failing:**
```bash
# Profile locally
python -m cProfile -s cumulative scripts/run_ingestion.py
memory_profiler your_script.py
# Check for bottlenecks
```

---

### Stage 7️⃣: Documentation
**Duration:** 1-2 minutes

```yaml
name: documentation
runs-on: ubuntu-latest

tools:
  - Sphinx (documentation generator)
  - API doc extractor
  - Markdown to HTML converter
```

**What it generates:**
- ✅ API documentation from docstrings
- ✅ README HTML version
- ✅ Architecture diagrams
- ✅ Code examples documentation

**Output:**
- Available in artifacts
- Can be deployed to GitHub Pages

**Fix if failing:**
```bash
# Check docstring format
python -m pydoc ingestion.arxiv_client
# Generate docs locally
sphinx-build -b html docs/ _build/
```

---

## 🎯 Monitoring Pipeline Execution

### Check Pipeline Status
```
GitHub Repository → Actions tab → Select workflow run
```

### View Real-Time Logs
```
Click on any stage → View raw logs
```

### Common Status Indicators
```
🟢 Success    - Stage passed all checks
🔴 Failed     - Stage failed, check logs
🟡 Running    - Stage currently executing
⚪ Skipped    - Stage skipped (due to condition)
⏸️  Queued    - Waiting to start
```

---

## 📊 Understanding Pipeline Results

### Success Run (🟢)
```
✅ code-quality: 3 checks passed
✅ security: 0 vulnerabilities found
✅ unit-tests: 45 tests passed, 82% coverage
✅ integration-tests: All scenarios passed
✅ docker-build: Image pushed successfully
✅ performance: All benchmarks within limits
✅ documentation: Generated 150 pages

RESULT: Success ✅
```

### Failed Run (🔴)
```
✅ code-quality: Passed
✅ security: Passed
❌ unit-tests: 2 tests failed
   └─ test_validation_pydantic.py::test_invalid_date_format
   └─ test_cassandra_insert.py::test_connection_timeout

RESULT: Failed (stopping pipeline)
ACTION: Fix failing tests and push again
```

---

## 🔧 Debugging Failed Stages

### Check Logs
```bash
# View logs of failed job in GitHub UI
# Or download as artifact
```

### Re-run Pipeline
```
GitHub UI → Re-run all jobs
Or: Re-run failed jobs only
```

### Common Failures & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `black --check failed` | Code formatting | Run: `black .` |
| `isort --check failed` | Import order | Run: `isort .` |
| `pytest failed` | Test failure | Run: `pytest tests/ -v` |
| `Docker build failed` | Dependency issue | Check `requirements.txt` |
| `Coverage <80%` | Insufficient tests | Add more test cases |
| `Trivy found vulnerabilities` | Outdated packages | Update dependencies |

---

## 📈 Expected Metrics

### Code Quality
- Lint score: 9.5-10/10
- Cyclomatic complexity: <5
- Maintainability index: >80

### Test Coverage
- Target: >80%
- Typical: 82-90%
- Core modules: 95%+

### Performance
- ETL execution: 30-40 seconds
- ELT execution: 40-45 minutes
- API response: <5 seconds
- Database query: <500ms

### Security
- Vulnerabilities: 0
- CodeQL issues: 0-3 (low severity)
- Outdated packages: <2

---

## 🚀 Deployment from Pipeline

### Manual Deployment
After successful pipeline run:
```bash
# Pull latest image
docker pull ghcr.io/USERNAME/research-papers-pipeline:latest

# Deploy to K8s/AKS/GKE
kubectl set image deployment/arxiv \
  arxiv=ghcr.io/USERNAME/research-papers-pipeline:latest
```

### Automatic Deployment
Configure GitHub Actions deployment trigger:
```yaml
- name: Deploy to Production
  if: github.ref == 'refs/heads/main'
  run: |
    # Deploy commands here
```

---

## 📞 Troubleshooting

### Pipeline Stuck
```
Check: Are services (Cassandra, Kafka) starting?
Fix: Increase service startup time in workflow
```

### Out of Disk Space
```
GitHub Actions has 29 GB available
Check: Are artifacts accumulating?
Fix: Configure artifact retention policy
```

### Timeout Issues
```
Default: 6 hours per job
Solution: Optimize slow stages
Check: Reduce test dataset size
```

---

## 🎓 Learning Resources

- **GitHub Actions Docs:** https://docs.github.com/actions
- **Workflow Syntax:** https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions
- **Python Testing:** https://pytest.readthedocs.io/
- **Docker CI/CD:** https://docs.docker.com/build/ci/github-actions/

---

**Last Updated:** May 25, 2026  
**Pipeline Version:** 1.0  
**Status:** ✅ Production Ready
