# Updated generate_embeddings.py with examples_revised.json and business_doc schema integration
import json
import os
from sentence_transformers import SentenceTransformer
import logging

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2'
OUTPUT_FILE = 'context/all_embeddings.json'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
        items_to_embed = []
        embedded_items = []

        logging.info(f"Processing source type: {source_type}")

        try:
            if source_info["source"] == "hardcoded":
                items_to_embed = source_info["data"]
                logging.info(f"Loaded {len(items_to_embed)} hardcoded items for '{source_type}'.")
            else:
                source_path = source_info["source"]
                if not os.path.exists(source_path):
                    logging.warning(f"Input file not found for '{source_type}': {source_path}. Skipping.")
                    continue
                with open(source_path, "r") as f:
                    items_to_embed = json.load(f)
                logging.info(f"Loaded {len(items_to_embed)} items from '{source_path}'.")
        except json.JSONDecodeError as e:
            logging.error(f"Error reading JSON file {source_info.get('source', 'hardcoded')}: {e}. Skipping '{source_type}'.")
            continue
        except Exception as e:
            logging.error(f"Error loading data for '{source_type}': {e}. Skipping.")
            continue

        for item in items_to_embed:
            try:
                text_to_embed = item.get(text_field)
                if text_to_embed is None:
                    logging.warning(f"Missing text field '{text_field}' in item for '{source_type}'. Skipping item.")
                    continue

                embedding = model.encode(text_to_embed).tolist()
                output_item = item.copy()
                output_item["embedding"] = embedding
                if 'type' not in output_item:
                    output_item['type'] = source_type
                embedded_items.append(output_item)

            except Exception as e:
                logging.error(f"Failed to embed item for '{source_type}' ('{str(item.get(text_field, 'N/A'))[:50]}...'): {e}")

        all_embeddings.setdefault(source_type, []).extend(embedded_items)
        logging.info(f"Finished embedding {len(embedded_items)} items for '{source_type}'.")

    output_path = os.path.join(PROJECT_ROOT, OUTPUT_FILE)
    logging.info(f"Saving all embeddings to: {output_path}")
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(all_embeddings, f, indent=2)
        logging.info("✅ Successfully saved all embeddings.")
    except Exception as e:
        logging.error(f"❌ Failed to save embeddings to {output_path}: {e}")

if __name__ == "__main__":
    generate_embeddings()
