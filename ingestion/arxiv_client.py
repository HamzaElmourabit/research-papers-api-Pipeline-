import arxiv

class ArxivClient:
    def __init__(self, batch_size: int = 100):
        
        self.batch_size = batch_size

    def search_papers(self ,category: str):
        search= arxiv.Search(
            query=f"cat:{category}",
            max_results=self.batch_size,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        return search.results()



