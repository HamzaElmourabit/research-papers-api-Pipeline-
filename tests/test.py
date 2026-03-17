import arxiv

client = arxiv.Client()

search = arxiv.Search(
    query="all",
    max_results=2
)

result = next(client.results(search))

for field, value in vars(result).items():
    if field=="categories":
     print(field,":",value)
