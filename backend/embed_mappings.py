import json
from sentence_transformers import SentenceTransformer

# Load the embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Define our DQL guidelines
guidelines = [
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

embedded_guidelines = []

# Loop through and embed each guideline
for item in guidelines:
    try:
        embedding = model.encode(item["nl"]).tolist()
        item["embedding"] = embedding
        embedded_guidelines.append(item)
        print(f"✅ Embedded: {item['nl'][:50]}...")
    except Exception as e:
        print(f"❌ Failed: {item['nl'][:50]} — {e}")

# Save to disk
with open("embedded_guidelines.json", "w") as f:
    json.dump(embedded_guidelines, f, indent=2)
    
print("✅ All embedded guidelines saved to 'embedded_guidelines.json'")

'''
Loading your model
Defining your guidelines
Creating embeddings for each guideline
Saving the embedded guidelines to a JSON file
'''