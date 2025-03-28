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

    # Wait for the index to become ready using polling
    print(f"Waiting for index '{INDEX_NAME}' to become ready (polling up to 120s)...")
    start_time = time.time()
    max_wait_seconds = 120
    check_interval_seconds = 5
    health_url = f"{ELASTIC_URL}/_cluster/health/{INDEX_NAME}"
    index_ready = False

    while time.time() - start_time < max_wait_seconds:
        try:
            health_response = requests.get(health_url, timeout=10) # Short timeout for each poll
            health_response.raise_for_status()
            health_data = health_response.json()
            status = health_data.get("status")

            if status in ["green", "yellow"]:
                print(f"✅ Index '{INDEX_NAME}' is ready (status: {status}).")
                index_ready = True
                break
            else:
                print(f"Index status: {status}. Waiting...")

        except requests.exceptions.Timeout:
            print("Polling request timed out. Retrying...")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error checking index health during polling: {e}")
            # Decide if this error is fatal or if polling should continue
            # For now, let's exit on persistent errors
            time.sleep(check_interval_seconds) # Wait before retrying after error
            # Could add a retry counter here if needed

        time.sleep(check_interval_seconds)

    if not index_ready:
        print(f"⚠️ Timed out after {max_wait_seconds}s waiting for index '{INDEX_NAME}' to become ready.")
        # Try to get allocation explanation
        print("Attempting to get shard allocation explanation...")
        explain_url = f"{ELASTIC_URL}/_cluster/allocation/explain"
        try:
            explain_response = requests.get(explain_url, timeout=10)
            explain_response.raise_for_status()
            print("--- Allocation Explanation ---")
            print(json.dumps(explain_response.json(), indent=2))
            print("-----------------------------")
        except requests.exceptions.RequestException as explain_e:
            print(f"❌ Could not get allocation explanation: {explain_e}")
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
