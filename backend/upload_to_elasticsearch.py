import json
import requests

ELASTIC_URL = "http://localhost:9200"
INDEX_NAME = "dql_schema"

# 1. Create the index with mapping (if it doesn't exist)
mapping = {
    "mappings": {
        "properties": {
            "object_type": { "type": "keyword" },
            "attribute": { "type": "keyword" },
            "type": { "type": "keyword" },
            "description": { "type": "text" },
            "source_text": { "type": "text" },
            "embedding": {
                "type": "dense_vector",
                "dims": 384,
                "index": True,
                "similarity": "cosine"
            }
        }
    }
}

index_url = f"{ELASTIC_URL}/{INDEX_NAME}"
response = requests.put(index_url, json=mapping)

if response.status_code in [200, 201]:
    print(f"✅ Index '{INDEX_NAME}' created or already exists.")
else:
    print(f"⚠️ Failed to create index: {response.text}")

# 2. Load embedded schema
with open("embedded_schema.json", "r") as f:
    records = json.load(f)

# 3. Bulk upload
bulk_data = ""
for i, doc in enumerate(records):
    action = { "index": { "_index": INDEX_NAME, "_id": i } }
    bulk_data += json.dumps(action) + "\n"
    bulk_data += json.dumps(doc) + "\n"

bulk_response = requests.post(
    f"{ELASTIC_URL}/_bulk",
    data=bulk_data,
    headers={"Content-Type": "application/x-ndjson"}
)

if bulk_response.status_code == 200 and not bulk_response.json().get("errors", True):
    print("✅ All documents uploaded successfully.")
else:
    print("❌ Errors occurred during upload.")
    print(bulk_response.text)
