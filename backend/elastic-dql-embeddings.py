import json
import requests
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
load_dotenv()

# CONFIG
ELASTIC_URL = os.getenv("ELASTIC_URL")
INDEX_NAME = "dql_guidelines"
MODEL_NAME = "all-MiniLM-L6-v2"

# Define our DQL guidelines
guidelines = [
    {
        "type": "synonym",
        "title": "Document Synonyms",
        "source_text": "A document could be referred to as a record, item, stuff, files",
        "content": {
            "entity": "document",
            "synonyms": ["record", "item", "stuff", "files"]
        }
    },
    {
        "type": "pattern",
        "title": "Pre-prevision ID Pattern",
        "source_text": "If the prompt includes the word pre-prevision, it's referring to something with id that begins with 'ph' followed by a number, ph1, ph2, ph3, phN...",
        "content": {
            "trigger": "pre-prevision",
            "pattern": "ph\\d+",
            "prefix": "ph"
        }
    },
    {
        "type": "pattern",
        "title": "Financial ID Pattern",
        "source_text": "Financial documents have IDs starting with 'fin' followed by 4 digits",
        "content": {
            "trigger": "financial",
            "pattern": "fin\\d{4}",
            "prefix": "fin"
        }
    }
]

# Step 1: Load embedding model
print(f"Loading model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)

# Step 2: Create embedded documents
print("Embedding guidelines...")
embedded_docs = []
for i, guideline in enumerate(guidelines):
    try:
        embedding = model.encode(guideline["source_text"]).tolist()
        embedded_doc = {
            "type": guideline["type"],
            "title": guideline["title"],
            "content": guideline["content"],
            "source_text": guideline["source_text"],
            "embedding": embedding
        }
        embedded_docs.append(embedded_doc)
        print(f"✅ Embedded: {guideline['title']}")
    except Exception as e:
        print(f"❌ Failed to embed {guideline.get('title', 'unknown')} — {e}")

# Step 3: Save to file (optional but good for backup)
with open("embedded_guidelines.json", "w") as f:
    json.dump(embedded_docs, f, indent=2)
print("✅ Saved embedded guidelines to 'embedded_guidelines.json'")

# Step 4: Check if index exists, if not create it with proper mapping for embeddings
def setup_index():
    # Check if index exists
    resp = requests.head(f"{ELASTIC_URL}/{INDEX_NAME}")
    
    if resp.status_code == 404:
        print(f"Creating index '{INDEX_NAME}'...")
        
        # Define mapping with dense_vector field for embeddings
        mapping = {
            "mappings": {
                "properties": {
                    "type": {"type": "keyword"},
                    "title": {"type": "text"},
                    "source_text": {"type": "text"},
                    "content": {"type": "object"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384,  # The dimension of all-MiniLM-L6-v2 embeddings
                        "index": True,
                        "similarity": "cosine"
                    }
                }
            }
        }
        
        # Create index with mapping
        resp = requests.put(
            f"{ELASTIC_URL}/{INDEX_NAME}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(mapping)
        )
        
        if resp.status_code >= 200 and resp.status_code < 300:
            print(f"✅ Index '{INDEX_NAME}' created successfully")
        else:
            print(f"❌ Failed to create index: {resp.text}")
            return False
    return True

# Step 5: Prepare and send bulk upload
def upload_documents():
    print(f"Uploading {len(embedded_docs)} documents to Elasticsearch...")
    
    # Prepare bulk payload
    bulk_payload = ""
    for i, doc in enumerate(embedded_docs):
        action = {"index": {"_index": INDEX_NAME, "_id": f"{doc['type']}_{i}"}}
        bulk_payload += json.dumps(action) + "\n"
        bulk_payload += json.dumps(doc) + "\n"
    
    # Send to Elasticsearch
    resp = requests.post(
        f"{ELASTIC_URL}/_bulk",
        headers={"Content-Type": "application/x-ndjson"},
        data=bulk_payload
    )
    
    # Report results
    if resp.status_code == 200 and not resp.json().get("errors", True):
        print("✅ All documents uploaded successfully.")
    else:
        print("❌ Upload failed.")
        print(resp.text)

# Main execution
if __name__ == "__main__":
    # Setup index first
    if setup_index():
        # Then upload documents
        upload_documents()
        
        # Demonstrate how to query (optional)
        print("\nTo query these embeddings, you can use:")
        print("""
    GET /dql_guidelines/_search
    {
      "query": {
        "script_score": {
          "query": {"match_all": {}},
          "script": {
            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
            "params": {
              "query_vector": <YOUR_QUERY_VECTOR>
            }
          }
        }
      }
    }
        """)
