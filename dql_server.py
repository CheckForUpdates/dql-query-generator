# dql_server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dql_logic import generate_dql

app = FastAPI()

# CORS so React can talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"message": "running..."}

@app.post("/generate")
def generate(request: QueryRequest):
    dql, timestamp = generate_dql(request.query)
    return { "dql": dql, "timestamp": timestamp }
