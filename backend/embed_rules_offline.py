from sentence_transformers import SentenceTransformer
import json

model = SentenceTransformer("all-MiniLM-L6-v2")

with open("rules_embedding.json") as f:
    rules = json.load(f)

embedded_rules = []
for rule in rules:
    embedding = model.encode(rule["source_text"]).tolist()
    embedded_rules.append({
        "type": rule["type"],
        "title": rule["title"],
        "content": rule["content"],
        "embedding": embedding
    })

with open("embedded_rules.json", "w") as f:
    json.dump(embedded_rules, f, indent=2)
