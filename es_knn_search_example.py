# Elasticsearch KNN search example
# Assuming you have a 384-dim vector from the model above

# Example Python snippet using requests:
import requests

query_vector = [...]  # ← Your embedded user input here

response = requests.post(
    "http://localhost:9200/dql_schema/_search",
    headers={"Content-Type": "application/json"},
    json={
        "size": 5,
        "knn": {
            "field": "embedding",
            "query_vector": query_vector,
            "k": 5,
            "num_candidates": 100
        }
    }
)

for hit in response.json()["hits"]["hits"]:
    print(hit["_source"]["attribute"], "→", hit["_score"])
