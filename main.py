from ingestion.fetch_papers import PaperFetcher
from ingestion.validation import validate_paper
from casandra.insert_papers import insert_papers

def run_pipeline():

    # ── 1. Extract ───────────────────────────────────────────────
    print("Fetching papers from arXiv...")
    fetcher = PaperFetcher(batch_size=10)  # keep small for first test
    raw_papers = fetcher.fetch_papers()
    print(f"  Fetched : {len(raw_papers)} papers")

    # ── 2. Validate ──────────────────────────────────────────────
    print("Validating papers...")
    valid_papers = validate_paper(raw_papers)
    dropped = len(raw_papers) - len(valid_papers)
    print(f"  Valid   : {len(valid_papers)} papers")
    print(f"  Dropped : {dropped} papers")

    # ── 3. Load ──────────────────────────────────────────────────
    print("Inserting into Cassandra...")
    summary = insert_papers(valid_papers)
    print(f"  Batch ID : {summary['batch_id']}")
    print(f"  Ingestion Date : {summary['ingestion_date']}")
    print(f"  Inserted : {summary['inserted']}/{summary['total']}")
    print(f"  Failed   : {summary['failed']}")

    return summary

if __name__ == "__main__":
    run_pipeline()