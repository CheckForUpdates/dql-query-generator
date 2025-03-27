import json
from sentence_transformers import SentenceTransformer

# Load the embedding model locally
model = SentenceTransformer('all-MiniLM-L6-v2')  # You can swap this with 'BAAI/bge-small-en' too

# Load the flattened schema
with open("flattened_schema.json", "r") as f:
    records = json.load(f)

embedded_records = []

# Loop through and embed each source_text
for item in records:
    text = item["source_text"]
    try:
        embedding = model.encode(text).tolist()  # Convert numpy array to list
        item["embedding"] = embedding
        embedded_records.append(item)
        print(f"✅ Embedded: {item['object_type']} → {item['attribute']}")
    except Exception as e:
        print(f"Failed to embed {item['attribute']} — {e}")

# Save to JSON
with open("embedded_schema.json", "w") as f:
    json.dump(embedded_records, f, indent=2)

print("All embeddings saved to 'embedded_schema.json'")
