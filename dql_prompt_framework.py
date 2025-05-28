# dql_prompt_framework.py

import requests
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
ELASTIC_URL = "http://129.158.33.207:9200"
INDEX_NAME = "dql_schema"
TOP_K = 5

# Load embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Load Gemini config from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# Setup Gemini API
if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY environment variable")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

def retrieve_context(user_input, k=TOP_K):
    query_vector = embed_model.encode(user_input).tolist()
    
    es_query = {
        "size": 20,
        "knn": {
            "field": "embedding",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": 100
        }
    }

    res = requests.post(f"{ELASTIC_URL}/{INDEX_NAME}/_search", json=es_query)
    hits = res.json().get("hits", {}).get("hits", [])

    grouped_context = {
        "schema": [],
        "example": [],
        "guideline": [],
        "pattern": [],
        "mapping": [],
        "glossary": [],
        "intent_hint": [],
        "policy": [],
        "user_context": []
    }

    for hit in hits:
        doc = hit["_source"]
        doc_type = doc.get("type")
        if doc_type in grouped_context:
            grouped_context[doc_type].append(doc)

    return grouped_context

def build_prompt(user_input, context):
    parts = []

    parts.append("You are a Documentum DQL assistant.")
    parts.append("Use the following schemas, guidelines, and examples to answer accurately.")

    if context["user_context"]:
        parts.append("\nUser context:")
        for item in context["user_context"]:
            parts.append(f"- {item['content']}")

    if context["glossary"]:
        parts.append("\nGlossary:")
        for item in context["glossary"]:
            parts.append(f"- {item['title']}: {item['content']}")

    if context["guideline"] or context["pattern"] or context["policy"]:
        parts.append("\nGuidelines and Policies:")
        for g in context["guideline"] + context["pattern"] + context["policy"]:
            parts.append(f"- {g['content']}")

    if context["schema"]:
        parts.append("\nSchema attributes:")
        for s in context["schema"]:
            parts.append(f"- {s['attribute']}: {s['description']}")

    if context["example"]:
        parts.append("\nExample Queries:")
        for ex in context["example"]:
            parts.append(f"- NL: {ex['nl']}\n  DQL: {ex['dql']}")

    parts.append(f"\nUser request:\n\"{user_input}\"")
    parts.append("\nDQL query:")

    return "\n".join(parts)

def generate_dql(user_input):
    context = retrieve_context(user_input)
    prompt = build_prompt(user_input, context)
    print("Context injected into prompt:")
    for item in context["user_context"]:
        print("-", item["content"])
    
    response = model.generate_content(prompt)
    return response.text.strip(), prompt

# Example usage
if __name__ == "__main__":
    user_input = "How many documents are in my cabinet?"
    dql, prompt_used = generate_dql(user_input)
    print("Prompt:\n" + prompt_used)
    print("\nGenerated DQL:\n" + dql)