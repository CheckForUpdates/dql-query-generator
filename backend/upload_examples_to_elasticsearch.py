import json
import requests

ELASTIC_URL = "http://localhost:9200"
INDEX_NAME = "dql_schema"

# Step 1: Load embedded examples
with open("embedded_examples.json", "r") as f:
    examples = json.load(f)

# Step 2: Create/update the index (if needed)
mapping = {
    "mappings": {
        "properties": {
            "type": { "type": "keyword" },
            "nl": { "type": "text" },
            "dql": { "type": "text" },
            "embedding": {
                "type": "dense_vector",
                "dims": 384,
                "index": True,
                "similarity": "cosine"
            }
        }
    }
}

# Only create the index if it doesn't exist
index_url = f"{ELASTIC_URL}/{INDEX_NAME}"
check_response = requests.get(index_url)
if check_response.status_code == 404:
    create_response = requests.put(index_url, json=mapping)
    if create_response.status_code in [200, 201]:
        print(f"✅ Index '{INDEX_NAME}' created.")
    else:
        print(f"❌ Failed to create index: {create_response.text}")
else:
    print(f"ℹ️ Index '{INDEX_NAME}' already exists — continuing upload.")

# Step 3: Upload documents
bulk_data = ""
for i, doc in enumerate(examples):
    action = { "index": { "_index": INDEX_NAME, "_id": f"example_{i}" } }
    bulk_data += json.dumps(action) + "\n"
    bulk_data += json.dumps(doc) + "\n"

bulk_response = requests.post(
    f"{ELASTIC_URL}/_bulk",
    data=bulk_data,
    headers={"Content-Type": "application/x-ndjson"}
)

# Step 4: Confirm result
if bulk_response.status_code == 200 and not bulk_response.json().get("errors", True):
    print("✅ All examples uploaded successfully.")
else:
    print("❌ Errors occurred during upload:")
    print(bulk_response.text)
