# feedback_prompt_framework.py

import requests
from sentence_transformers import SentenceTransformer
import json
import os
from datetime import datetime
from typing import Dict, List

# Load embedder
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Config
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://129.158.33.207:9200")
INDEX_NAME = os.getenv("INDEX_NAME", "dql_schema")
TOP_K = 5


def retrieve_context(user_input: str, k: int = TOP_K) -> Dict[str, List[dict]]:
    """Query Elasticsearch and group results by type"""
    query_vector = embedder.encode(user_input).tolist()

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

    context = {
        "schema": [],
        "example": [],
        "guideline": [],
        "pattern": [],
        "mapping": [],
        "glossary": [],
        "intent_hint": [],
        "policy": [],
        "user_context": [],
        "feedback_example": []
    }

    for hit in hits:
        doc = hit["_source"]
        doc_type = doc.get("type")
        if doc_type in context:
            context[doc_type].append(doc)
        elif doc.get("source") == "feedback":
            context["feedback_example"].append(doc)

    return context


def build_prompt(user_input: str, context: Dict[str, List[dict]]) -> str:
    parts = ["You are a Documentum DQL assistant.",
             "Use the following schemas, guidelines, and examples to answer accurately."]

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

    if context["feedback_example"]:
        parts.append("\nUser-validated example queries:")
        for ex in context["feedback_example"][:3]:
            parts.append(f"- NL: {ex['nl']}\n  DQL: {ex['dql']}")

    if context["example"]:
        parts.append("\nExample queries:")
        for ex in context["example"][:3]:
            parts.append(f"- NL: {ex['nl']}\n  DQL: {ex['dql']}")

    parts.append(f"\nUser request:\n\"{user_input}\"")
    parts.append("\nDQL query:")

    return "\n".join(parts)


# Example usage
if __name__ == "__main__":
    user_input = "How many documents do I have in my cabinet?"
    context = retrieve_context(user_input)
    prompt = build_prompt(user_input, context)
    print(prompt)
