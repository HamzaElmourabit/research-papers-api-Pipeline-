# 📤 Push Project to GitHub - Complete Guide

This guide will help you push the project to GitHub.

---

## Step 1: Create GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Fill in:
   - **Repository name**: `research-papers-pipeline`
   - **Description**: `ETL + ELT Data Pipeline for Research Papers from arXiv`
   - **Public/Private**: Choose based on preference
   - ❌ DO NOT initialize with README (we already have one)
3. Click **Create repository**

---

## Step 2: Configure Git Locally

```bash
# Navigate to project directory
cd "C:\Users\khadi\Downloads\research papers api - Copy"

# Check git status
git status

# Configure git (first time only)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Verify configuration
git config --list
```

---

## Step 3: Update Remote URL

If you already have a local git repo:

```bash
# Check current remote
git remote -v

# Remove old remote (if any)
git remote remove origin

# Add new GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/research-papers-pipeline.git

# Verify
git remote -v
```

---

## Step 4: Prepare Files for Commit

```bash
# Stage all files
git add .

# Check what's staged
git status

# You should see:
# - New files (docs, scripts, notebooks)
# - Modified files (README.md, requirements.txt)
# - Ignored files (venv/, __pycache__, .tmp_dagster_home/, etc.)
```

---

## Step 5: Create Initial Commit

```bash
# Create commit with message
git commit -m "Initial commit: Complete ETL+ELT pipeline for research papers

- Dagster orchestration with arXiv API integration
- Cassandra database with schema and validation
- Databricks analytics with Bronze/Silver/Gold layers
- Complete documentation and deployment scripts
- Parquet export for downstream processing"

# Check log
git log --oneline -5
```

---

## Step 6: Push to GitHub

```bash
# Push to GitHub (first time)
git branch -M main
git push -u origin main

# For subsequent pushes
git push origin main
```

---

## Step 7: Verify on GitHub

1. Go to `https://github.com/YOUR_USERNAME/research-papers-pipeline`
2. Verify you see:
   - ✅ README.md with full documentation
   - ✅ All folders (ingestion, pipelines, scripts, etc.)
   - ✅ requirements.txt
   - ✅ docker-compose.yml
   - ✅ .gitignore
   - ✅ Documentation files

---

## Common Git Commands

```bash
# Check status
git status

# View recent commits
git log --oneline -10

# View changes
git diff

# Add specific file
git add path/to/file

# Unstage file
git reset path/to/file

# Undo last commit (keep changes)
git reset --soft HEAD~1

# View remote
git remote -v

# Sync with remote
git pull origin main
```

---

## If You Have Issues

### Authentication Error
```bash
# Use GitHub token instead of password
# 1. Generate token: https://github.com/settings/tokens
# 2. When asked for password, paste the token instead
# 3. Or use SSH: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
```

### File Too Large
```bash
# Check what's pushing
git diff --cached --stat

# Remove large files (if > 100MB)
git rm --cached path/to/large/file
git commit -m "Remove large file"
```

### Wrong Branch Name
```bash
# Rename main branch
git branch -M main

# Or push to different branch
git push -u origin your-branch-name
```

---

## After Push: Update Project Settings

### On GitHub Website:

1. **Settings → General**
   - Add description
   - Add homepage URL
   - Choose license (MIT recommended)

2. **Settings → Branches**
   - Set main as default branch
   - Add branch protection rules (optional)

3. **Settings → Secrets**
   - Add environment variables if needed later

4. **Add Topics**
   - Click "Add topics"
   - Add: `etl`, `elt`, `dagster`, `databricks`, `cassandra`, `arxiv`, `data-engineering`

---

## Optional: Add GitHub Workflows

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/
```

---

## Final Checklist

- ✅ .gitignore created
- ✅ README.md updated
- ✅ requirements.txt current
- ✅ .env.example configured
- ✅ Git initialized and configured
- ✅ Remote URL set correctly
- ✅ Files staged and committed
- ✅ Pushed to GitHub
- ✅ Verified on GitHub website

---

**You're done!** 🎉 Your project is now on GitHub!

Next steps:
- Share the link: `https://github.com/YOUR_USERNAME/research-papers-pipeline`
- Add collaborators if needed
- Set up CI/CD workflows
