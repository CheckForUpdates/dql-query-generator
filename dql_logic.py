# dql_logic.py
import os
import json
import requests
from datetime import datetime
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Gemini API setup
genai.configure(api_key="AIzaSyAIremlgEW9JctWWK7ns-rRjsz67BF8x60")


# Load embedding model
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")


# ElasticSearch config
ELASTIC_URL = "http://localhost:9200"
INDEX_NAME = "dql_schema"
TOP_K = 5

def format_schema(doc): return f"{doc['attribute']}: {doc['description']}"
def format_example(doc): return f"Example: {doc['nl']} → {doc['dql']}"
def format_guideline(doc): return f"Guideline: {doc['content']}"
def format_intent(doc): return f"Intent Hint: {doc['content']}"
def format_glossary(doc): return f"Definition - {doc['title']}: {doc['content']}"
def format_policy(doc): return f"Policy Rule: {doc['content']}"
def format_user_context(doc): return f"Session Context: {doc['content']}"

FORMATTERS = {
    "schema": format_schema,
    "example": format_example,
    "guideline": format_guideline,
    "intent_hint": format_intent,
    "glossary": format_glossary,
    "policy": format_policy,
    "user_context": format_user_context
}

def generate_dql(user_input: str) -> tuple[str, str]:
    # Step 1: Embed the query
    query_vector = embed_model.encode(user_input).tolist()

    # Step 2: Query Elasticsearch
    query = {
        "size": TOP_K,
        "knn": {
            "field": "embedding",
            "query_vector": query_vector,
            "k": TOP_K,
            "num_candidates": 100
        }
    }

    response = requests.post(
        f"{ELASTIC_URL}/{INDEX_NAME}/_search",
        headers={"Content-Type": "application/json"},
        json=query
    )

    results = response.json().get("hits", {}).get("hits", [])
    schema_context = []
    for hit in results:
        src = hit["_source"]
        doc_type = src.get("type")
        formatter = FORMATTERS.get(doc_type)

        if formatter:
            schema_context.append(formatter(src))
        else:
            # fallback or log unhandled types
            schema_context.append(f"Unhandled type: {doc_type}")
            
    # schema_context = []
    # for hit in results:
    #     src = hit["_source"]
    #     if src.get("type") == "schema":
    #         schema_context.append(f"{src['attribute']}: {src['description']}")
    #     elif src.get("type") == "example":
    #         schema_context.append(f"Example: {src['nl']} → {src['dql']}")

    # Step 3: Create prompt
    prompt = f"""You are a Documentum DQL assistant. Based on the schema and examples below, convert the user request into a DQL query.
        You do not need to explain the query.

Context:
{chr(10).join(schema_context)}

User request:
"{user_input}"

Respond ONLY with the generated DQL query, without any introductory text, explanation, or markdown formatting.
DQL query:"""

    # Call Gemini API
    response = model.generate_content(prompt)

    return response.text.strip(), str(datetime.now())
