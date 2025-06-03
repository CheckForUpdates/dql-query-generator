import pandas as pd
import json
from sentence_transformers import SentenceTransformer
from datetime import datetime

# Load feedback CSV
df = pd.read_csv("feedback.csv")

# Filter for good feedback
df_good = df[df['feedback'].str.lower() == 'good'].copy()

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Prepare examples
examples = []
for _, row in df_good.iterrows():
    nl = str(row['input']).strip()
    dql = str(row['query']).strip()
    comment = str(row.get('comment', '')).strip()
    timestamp = str(row.get('timestamp', datetime.utcnow().isoformat()))
    embedding = model.encode(nl).tolist()

    examples.append({
        "type": "example",
        "source": "feedback",
        "nl": nl,
        "dql": dql,
        "embedding": embedding,
        "tags": ["user_curated", "feedback"],
        "score": 1,
        "timestamp": timestamp,
        "comment": comment
    })

# Output to JSON
with open("context/feedback_examples.json", "w", encoding="utf-8") as f:
    json.dump(examples, f, indent=2)

print("✅ Saved to context/feedback_examples.json")
