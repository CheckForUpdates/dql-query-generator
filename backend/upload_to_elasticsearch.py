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

# 2. Load all embedded data
try:
    with open("context/all_embeddings.json", "r") as f:
        all_data = json.load(f)
    print("✅ Loaded consolidated embeddings from 'context/all_embeddings.json'.")
except FileNotFoundError:
    print("❌ Error: 'context/all_embeddings.json' not found. Run generate_embeddings.py first.")
    exit()
except json.JSONDecodeError:
    print("❌ Error: Failed to decode JSON from 'context/all_embeddings.json'.")
    exit()

# 3. Bulk upload
bulk_data = ""
doc_id_counter = 0
for data_type, records in all_data.items():
    print(f"Preparing '{data_type}' documents for bulk upload...")
    if not isinstance(records, list):
        print(f"⚠️ Skipping '{data_type}': Expected a list, but got {type(records)}.")
        continue
    for doc in records:
        # Ensure the document is a dictionary
        if not isinstance(doc, dict):
            print(f"⚠️ Skipping item in '{data_type}': Expected a dictionary, but got {type(doc)}.")
            continue
        # Ensure embedding exists and is a list (basic check)
        if 'embedding' not in doc or not isinstance(doc.get('embedding'), list):
            print(f"⚠️ Skipping item in '{data_type}' due to missing or invalid 'embedding': {str(doc)[:100]}...")
            continue

        action = { "index": { "_index": INDEX_NAME, "_id": doc_id_counter } }
        bulk_data += json.dumps(action) + "\n"
        bulk_data += json.dumps(doc) + "\n"
        doc_id_counter += 1

if not bulk_data:
    print("No valid documents found to upload.")
    exit()

print(f"Attempting to upload {doc_id_counter} documents...")

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
