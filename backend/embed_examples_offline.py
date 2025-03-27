import json
from sentence_transformers import SentenceTransformer

# Load the local embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Load the natural language → DQL examples
with open("examples_embeddings.json", "r") as f:
    examples = json.load(f)

embedded_examples = []

# Loop through and embed the natural language part
for item in examples:
    try:
        embedding = model.encode(item["nl"]).tolist()
        embedded_examples.append({
            "type": "example",
            "nl": item["nl"],
            "dql": item["dql"],
            "embedding": embedding
        })
        print(f"✅ Embedded: {item['nl'][:50]}...")
    except Exception as e:
        print(f"❌ Failed: {item['nl'][:50]} — {e}")

# Save to disk
with open("embedded_examples.json", "w") as f:
    json.dump(embedded_examples, f, indent=2)

print("✅ All embedded examples saved to 'embedded_examples.json'")
