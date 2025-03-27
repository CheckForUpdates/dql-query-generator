import json
import requests
from sentence_transformers import SentenceTransformer

# CONFIG
ELASTIC_URL = "http://localhost:9200"
INDEX_NAME = "dql_schema"
MODEL_NAME = "all-MiniLM-L6-v2"
FILE_PATH = "rules_embedding.json"

# Step 1: Load rules from file
with open(FILE_PATH, "r") as f:
    rules = json.load(f)

# Step 2: Load embedding model
model = SentenceTransformer(MODEL_NAME)

# Step 3: Create embedded documents
embedded_docs = []
for i, rule in enumerate(rules):
    try:
        embedding = model.encode(rule["source_text"]).tolist()
        embedded_doc = {
            "type": rule["type"],
            "title": rule["title"],
            "content": rule["content"],
            "embedding": embedding
        }
        embedded_docs.append(embedded_doc)
        print(f"Embedded: {rule['title']}")
    except Exception as e:
        print(f"Failed to embed {rule.get('title', 'unknown')} — {e}")

# Step 4: Prepare bulk upload
bulk_payload = ""
for i, doc in enumerate(embedded_docs):
    action = { "index": { "_index": INDEX_NAME, "_id": f"{doc['type']}_{i}" } }
    bulk_payload += json.dumps(action) + "\n"
    bulk_payload += json.dumps(doc) + "\n"

# Step 5: Send to Elasticsearch
resp = requests.post(
    f"{ELASTIC_URL}/_bulk",
    headers={"Content-Type": "application/x-ndjson"},
    data=bulk_payload
)

# Step 6: Report
if resp.status_code == 200 and not resp.json().get("errors", True):
    print("All documents uploaded successfully.")
else:
    print("Upload failed.")
    print(resp.text)
