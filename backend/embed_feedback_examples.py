import json
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Load feedback curated JSON
#input_path = Path("context/feedback_curated.json")
input_path = Path("context/feedback_examples.json")
with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Determine the list of entries to process
if isinstance(data, dict) and "feedback_entries" in data:
    entries_to_process = data.get("feedback_entries", [])
elif isinstance(data, list):
    entries_to_process = data
else:
    print("⚠️ Warning: Unexpected format in feedback_examples.json")
    entries_to_process = [] # Handle unexpected format

# Filter for good feedback
positive_entries = [
    fb for fb in entries_to_process
    if fb.get("score", 0) > 0 and fb.get("input") and fb.get("query")
]

# Load model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Build embeddings
embedded_feedback = []
for entry in positive_entries:
    embedding = model.encode(entry["input"]).tolist()
    embedded_feedback.append({
        "type": "example",
        "source": "feedback",
        "nl": entry["input"],
        "dql": entry["query"],
        "embedding": embedding,
        "tags": ["user_curated", "feedback"],
        "score": 1,
        "comment": entry.get("comment", "")
    })

# Save result
output_path = Path("context/feedback_examples.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(embedded_feedback, f, indent=2)

print("✅ Saved to context/feedback_examples.json")
