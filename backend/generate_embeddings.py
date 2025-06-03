import json
import os
from sentence_transformers import SentenceTransformer
import logging

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2'
OUTPUT_FILE = 'context/all_embeddings.json'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONTEXT_DIR = os.path.join(PROJECT_ROOT, "context")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Data Sources ---
DATA_SOURCES = [
    {
        "type": "guidelines",
        "source": "hardcoded",
        "text_field": "nl",
        "data": [
            {
                "type": "synonyms",
                "nl": "documents, folders and attributes might be defined differently by the user.",
                "document": ["record", "item", "stuff", "files", "doc"],
                "folder": ["directory", "folder", "location", "subfolder"],
                "attribute": ["property", "metadata", "info"]
            },
            {
                "type": "patterns",
                "trigger": ["pre-provision", "preprovision"],
                "pattern": "pp\\d+",
                "prefix": "pp",
                "nl": "Pre provisioned cabinet ids begin with pp followed by a number. pp1, pp2, pp3, ppN..."
            },
            {
                "type": "queryTemplates",
                "basicSelect": "SELECT {attributes} FROM {objectType} WHERE {conditions}",
                "folderQuery": "SELECT {attributes} FROM {objectType} WHERE FOLDER('/{folderPath}')",
                "subfolderQuery": "SELECT {attributes} FROM {objectType} WHERE FOLDER('/{folderPath}', DESCEND)'",
                "nl": "Basic SELECT statements"
            },
            {
                "type": "Migration",
                "trigger": ["RIMA", "Migration"],
                "pattern": "RIMA_\\d+",
                "prefix": "RIMA_",
                "nl": "Cabinets that begin with 'RIMA_' are reserved for the RIMA to DMS migration."
            }
        ]
    },
    {
        "type": "examples",
        "source": os.path.join(PROJECT_ROOT, "context/examples_revised.json"),
        "text_field": "nl"
    },
    {
        "type": "rules",
        "source": os.path.join(PROJECT_ROOT, "context/rules_embedding.json"),
        "text_field": "source_text"
    },
    {
        "type": "schema",
        "source": os.path.join(PROJECT_ROOT, "flattened_schema.json"),
        "text_field": "source_text"
    },
    {
        "type": "schema",
        "source": os.path.join(PROJECT_ROOT, "context/business_doc_schema.json"),
        "text_field": "source_text"
    },
    {
        "type": "user_context",
        "source": os.path.join(PROJECT_ROOT, "context/user_context.json"),
        "text_field": "content"
    },
    {
        "type": "feedback",
        "source": os.path.join(PROJECT_ROOT, "context/feedback_examples.json"),
        "text_field": "nl"
    }
]

def generate_embeddings():
    logging.info(f"Loading embedding model: {MODEL_NAME}")
    try:
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        logging.error(f"Failed to load model {MODEL_NAME}: {e}")
        return

    all_embeddings = {}

    for source_info in DATA_SOURCES:
        source_type = source_info["type"]
        text_field = source_info["text_field"]
        embedded_items = []

        logging.info(f"Processing source type: {source_type}")

        try:
            if source_info["source"] == "hardcoded":
                items_to_embed = source_info["data"]
            else:
                with open(source_info["source"], "r", encoding="utf-8") as f:
                    items_to_embed = json.load(f)
        except Exception as e:
            logging.error(f"❌ Failed to load data for {source_type}: {e}")
            continue

        # Special handling for feedback
        if source_type == "feedback":
            for entry in items_to_embed:
                if not entry.get("nl") or not entry.get("dql"):
                    continue
                try:
                    embedding = model.encode(entry["nl"]).tolist()
                    feedback_type = "feedback_positive" if entry.get("score", 0) > 0 else "feedback_negative"
                    item = {
                        "type": feedback_type,
                        "source": "feedback",
                        "nl": entry["nl"],
                        "dql": entry["dql"],
                        "embedding": embedding,
                        "tags": entry.get("tags", []) + ["feedback"],
                        "score": entry.get("score", 0),
                        "comment": entry.get("comment", "")
                    }
                    embedded_items.append(item)
                except Exception as e:
                    logging.error(f"Failed to embed feedback entry: {e}")
        else:
            for item in items_to_embed:
                try:
                    text_to_embed = item.get(text_field)
                    if not text_to_embed:
                        continue
                    embedding = model.encode(text_to_embed).tolist()
                    output_item = item.copy()
                    output_item["embedding"] = embedding
                    if 'type' not in output_item:
                        output_item["type"] = source_type
                    embedded_items.append(output_item)
                except Exception as e:
                    logging.error(f"Failed to embed item from {source_type}: {e}")

        all_embeddings.setdefault(source_type, []).extend(embedded_items)
        logging.info(f"✅ Embedded {len(embedded_items)} items for {source_type}")

    # Save to disk
    output_path = os.path.join(PROJECT_ROOT, OUTPUT_FILE)
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_embeddings, f, indent=2)
        logging.info(f"✅ Saved all embeddings to {output_path}")
    except Exception as e:
        logging.error(f"❌ Failed to save output: {e}")

if __name__ == "__main__":
    generate_embeddings()
