"""
Test Cassandra insertion via Docker cqlsh (Python 3.13 compatible approach)
"""
import sys
import datetime

# Test the new insert_papers function
from casandra.insert_papers import insert_papers

# Sample papers
test_papers = [
    {
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
    },
    {
        "arxiv_id": "2401.00002",
        "title": "Test Paper 2: Deep Learning with Special Characters: O'Neill's Method",
        "abstract": "Testing special characters like quotes and apostrophes.",
        "authors": ["Charlie O'Brien"],
        "categories": ["cs.AI"],
        "primary_category": "cs.AI",
        "published_date": "2024-01-16",
        "updated_date": "2024-01-17",
        "pdf_url": "https://arxiv.org/pdf/2401.00002.pdf",
        "raw_json": '{"id": "2401.00002"}',
        "ingested_at": datetime.datetime.now().isoformat(),
    },
]

print("=" * 70)
print("Testing Cassandra insertion via Docker cqlsh (Python 3.13 compatible)")
print("=" * 70)

try:
    result = insert_papers(test_papers)
    
    print(f"\n✅ Insertion completed!")
    print(f"   Batch ID: {result['batch_id']}")
    print(f"   Ingestion Date: {result['ingestion_date']}")
    print(f"   Total Papers: {result['total']}")
    print(f"   Inserted: {result['inserted']}")
    print(f"   Failed: {result['failed']}")
    
    if result['failed'] == 0:
        print(f"\n🎉 All papers inserted successfully!")
    else:
        print(f"\n⚠️  {result['failed']} papers failed to insert")
        
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
