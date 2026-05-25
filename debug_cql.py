"""
Debug: Check the CQL statement being generated
"""
import uuid
import datetime

batch_id = uuid.uuid4()
ingestion_date = datetime.date.today().isoformat()

paper = {
    "arxiv_id": "2401.00001",
    "title": "Test Paper 1: Machine Learning",
    "abstract": "This is a test abstract for the first paper.",
    "authors": ["Alice Johnson", "Bob Smith"],
    "categories": ["cs.LG", "stat.ML"],
    "primary_category": "cs.LG",
    "published_date": "2024-01-15",
    "updated_date": "2024-01-16",
    "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf",
    "raw_json": '{"id": "2401.00001"}',
    "ingested_at": datetime.datetime.now().isoformat(),
}

# Escape single quotes in strings
title_escaped = paper.get("title", "").replace("'", "''")
abstract_escaped = paper.get("abstract", "").replace("'", "''")
raw_json_escaped = paper.get("raw_json", "{}").replace("'", "''")

# Build CQL list literals for authors and categories
# Format: ['item1', 'item2', ...] for LIST type
authors_list = paper.get("authors", [])
if authors_list:
    authors_str = "[" + ",".join(f"'{a.replace(chr(39), chr(39)+chr(39))}'" for a in authors_list) + "]"
else:
    authors_str = "[]"

categories_list = paper.get("categories", [])
if categories_list:
    categories_str = "[" + ",".join(f"'{c.replace(chr(39), chr(39)+chr(39))}'" for c in categories_list) + "]"
else:
    categories_str = "[]"

cql = f"""INSERT INTO papers_raw (
    batch_id, ingestion_date, arxiv_id, title, abstract,
    authors, categories, primary_category,
    published_date, updated_date, pdf_url, raw_json, ingested_at
) VALUES (
    {batch_id},
    '{ingestion_date}',
    '{paper.get("arxiv_id", "")}',
    '{title_escaped}',
    '{abstract_escaped}',
    {authors_str},
    {categories_str},
    '{paper.get("primary_category", "")}',
    '{paper.get("published_date", "")}',
    '{paper.get("updated_date", "")}',
    '{paper.get("pdf_url", "")}',
    '{raw_json_escaped}',
    '{paper.get("ingested_at", "")}'
);"""

print("Generated CQL:")
print("=" * 70)
print(cql)
print("=" * 70)

# Try to run it directly
import subprocess
result = subprocess.run(
    ["docker", "exec", "cassandra_arxiv", "cqlsh", "-e", f"USE arxiv; {cql}"],
    capture_output=True,
    text=True,
    timeout=10
)

print(f"\nReturn code: {result.returncode}")
print(f"STDOUT:\n{result.stdout}")
print(f"STDERR:\n{result.stderr}")
