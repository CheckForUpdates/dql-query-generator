import json
import requests
import time # Add time import for delays

ELASTIC_URL = "http://localhost:9200"
INDEX_NAME = "dql_schema"
index_url = f"{ELASTIC_URL}/{INDEX_NAME}"

# 1. Delete existing index (if it exists) to prevent stale data
print(f"Attempting to delete existing index '{INDEX_NAME}'...")
delete_response = requests.delete(index_url)
if delete_response.status_code == 200:
    print(f"✅ Index '{INDEX_NAME}' deleted successfully.")
elif delete_response.status_code == 404:
    print(f"ℹ️ Index '{INDEX_NAME}' does not exist, no need to delete.")
else:
    print(f"⚠️ Failed to delete index: {delete_response.text}")

# 2. Create the new index with mapping
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

response = requests.put(index_url, json=mapping)

if response.status_code == 200:
    print(f"✅ Index '{INDEX_NAME}' created successfully.")

    # Wait for the index to become ready
    print(f"Waiting for index '{INDEX_NAME}' to become ready...")
    health_url = f"{ELASTIC_URL}/_cluster/health/{INDEX_NAME}?wait_for_status=yellow&timeout=60s"
    try:
        # Add a client-side timeout slightly longer than the server-side wait time
        health_response = requests.get(health_url, timeout=70)
        health_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        health_data = health_response.json()
        if health_data.get("timed_out"):
            print(f"⚠️ Timed out waiting for index '{INDEX_NAME}' to become ready.")
            exit()
        elif health_data.get("status") in ["green", "yellow"]:
             print(f"✅ Index '{INDEX_NAME}' is ready (status: {health_data.get('status')}).")
        else:
            print(f"⚠️ Index '{INDEX_NAME}' has unexpected status: {health_data.get('status')}.")
            exit()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error checking index health: {e}")
        exit()

else:
    print(f"⚠️ Failed to create index: {response.text}")
    exit() # Exit if index creation fails

# 3. Load all embedded data
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

# 4. Bulk upload
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
