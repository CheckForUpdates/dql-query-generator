import json
import os
from sentence_transformers import SentenceTransformer
import logging

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2'
OUTPUT_FILE = 'context/all_embeddings.json'
# Determine project root directory (assuming this script is in backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Data Source Definitions ---
# Define where to find the data and which field contains the text to embed
DATA_SOURCES = [
    {
        "type": "guidelines",
        "source": "hardcoded", # Special case, data is defined below
        "text_field": "nl",
        "data": [ # Data copied from embed_mappings.py
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
        "source": os.path.join(PROJECT_ROOT, "context/examples_embeddings.json"), # Assuming input is in context/
        "text_field": "nl"
        # Note: Original script read from and wrote to examples_embeddings.json.
        # Using context/examples_embeddings.json as INPUT here. Verify if this is correct.
    },
    {
        "type": "rules",
        "source": os.path.join(PROJECT_ROOT, "context/rules_embedding.json"), # Assuming input is in context/
        "text_field": "source_text"
    },
    {
        "type": "schema",
        "source": os.path.join(PROJECT_ROOT, "flattened_schema.json"), # Assuming input is in root
        "text_field": "source_text"
    }
]

# --- Main Embedding Function ---
def generate_embeddings():
    """Loads data, generates embeddings, and saves to a consolidated file."""
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

        # Load data
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

        # Embed items
        for item in items_to_embed:
            try:
                text_to_embed = item.get(text_field)
                if text_to_embed is None:
                    logging.warning(f"Missing text field '{text_field}' in item for '{source_type}'. Skipping item.")
                    # Optionally add the item without embedding, or skip entirely
                    # embedded_items.append(item) # Add without embedding
                    continue # Skip item

                embedding = model.encode(text_to_embed).tolist()
                # Create a copy to avoid modifying the original dict if loaded from file
                output_item = item.copy()
                output_item["embedding"] = embedding
                # Ensure 'type' field exists if not already present (like in schema)
                if 'type' not in output_item:
                     output_item['type'] = source_type
                embedded_items.append(output_item)
                logging.debug(f"Embedded item for '{source_type}': {str(text_to_embed)[:50]}...")

            except Exception as e:
                logging.error(f"Failed to embed item for '{source_type}' ('{str(item.get(text_field, 'N/A'))[:50]}...'): {e}")
                # Optionally add the item without embedding
                # embedded_items.append(item.copy())

        all_embeddings[source_type] = embedded_items
        logging.info(f"Finished embedding {len(embedded_items)} items for '{source_type}'.")

    # Save consolidated embeddings
    output_path = os.path.join(PROJECT_ROOT, OUTPUT_FILE)
    logging.info(f"Saving all embeddings to: {output_path}")
    try:
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(all_embeddings, f, indent=2)
        logging.info("✅ Successfully saved all embeddings.")
    except Exception as e:
        logging.error(f"❌ Failed to save embeddings to {output_path}: {e}")

if __name__ == "__main__":
    generate_embeddings()
