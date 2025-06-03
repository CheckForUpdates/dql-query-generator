from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import requests
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
load_dotenv()

# https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-exp-03-25:generateContent?key=AIzaSyAIremlgEW9JctWWK7ns-rRjsz67BF8x60
# --- Config ---
#ELASTIC_URL = "http://localhost:9200"
ELASTIC_URL = os.getenv("ELASTIC_URL")
INDEX_NAME = "dql_schema"
TOP_K = 5
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

# --- App Setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class PromptRequest(BaseModel):
    prompt: str

class QueryResponse(BaseModel):
    query: str
    timestamp: str

# --- Load Embedding Model ---
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# --- Routes ---
@app.post("/generate", response_model=QueryResponse)
async def generate_query(req: PromptRequest):
    prompt = req.prompt
    query_vector = embedder.encode(prompt).tolist()

    # Step 1: KNN Search Elasticsearch
    es_query = {
        "size": TOP_K,
        "knn": {
            "field": "embedding",
            "query_vector": query_vector,
            "k": TOP_K,
            "num_candidates": 100
        }
    }
    es_res = requests.post(f"{ELASTIC_URL}/{INDEX_NAME}/_search", json=es_query)
    hits = es_res.json().get("hits", {}).get("hits", [])

    field_lines = []
    examples = []
    for hit in hits:
        src = hit["_source"]
        if src.get("object_type") in ["business_cab", "record_class"]:
            field_lines.append(f"- {src['attribute']}: {src['description']}")
        elif src.get("type") == "example":
            examples.append(f"- NL: {src['nl']}\n  DQL: {src['dql']}")

    # Step 2: Build Prompt
    prompt_text = """You are a Documentum DQL assistant. Convert the user's request into a DQL query.\n"""
    if field_lines:
        prompt_text += f"\nAvailable fields:\n{chr(10).join(field_lines)}"
    if examples:
        prompt_text += f"\n\nExample queries:\n{chr(10).join(examples)}"
    prompt_text += f"\n\nUser request:\n\"{prompt}\"\n\nDQL query:"

    gemini_payload = {
        "contents": [
            {
                "parts": [{"text": prompt_text}]
            }
        ]
    }

    # Step 3: Call Gemini
    gemini_res = requests.post(
        GEMINI_API_URL,
        headers={"Content-Type": "application/json"},
        json=gemini_payload
    )

    if gemini_res.status_code == 200:
        dql = gemini_res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        dql = "-- Error generating DQL: " + gemini_res.text

    return QueryResponse(
        query=dql,
        timestamp=datetime.utcnow().isoformat()
    )
