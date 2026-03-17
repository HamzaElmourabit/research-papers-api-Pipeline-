from ingestion.arxiv_client import ArxivClient
import json
import datetime

ARXIV_DOMAINS = [
    "cs.AI",
    "cs.LG",
    "cs.CV",
    "cs.CL",
    "stat.ML"
]



class PaperFetcher:
    def __init__(self, batch_size: int = 100):
        self.client = ArxivClient(batch_size)

    def fetch_papers(self):
        papers=[]
        for domain in ARXIV_DOMAINS:
           

          for result in self.client.search_papers(domain):
           paper = {
            "arxiv_id": result.entry_id.split("/")[-1],
            "title": result.title,
            "abstract": result.summary,
            "authors": [a.name for a in result.authors],
            "categories": result.categories,
            "primary_category": result.primary_category,
            "published_date": result.published,
            "updated_date": result.updated,
            "pdf_url": result.pdf_url,
            "raw_json": json.dumps(result._raw),
            "ingested_at": datetime.datetime.utcnow()
          }
          papers.append(paper)
        return papers
