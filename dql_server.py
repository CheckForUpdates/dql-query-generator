# dql_server.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dql_prompt_framework import generate_dql
import datetime
import csv
import os

app = FastAPI()

# CORS so React can talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class FeedbackRequest(BaseModel):
    input: str
    query: str
    timestamp: str
    feedback: str  # 'good' or 'bad'
    comment: str = ""  # Optional comment

@app.get("/")
def read_root():
    return {"message": "DQL Assistant API is running..."}

@app.post("/generate")
def generate(request: QueryRequest):
    dql, _ = generate_dql(request.query)
    timestamp = datetime.datetime.now().strftime("%m/%d/%Y %I:%M %p")
    return {"dql": dql, "timestamp": timestamp}

@app.post("/feedback")
def receive_feedback(request: FeedbackRequest):
    feedback_file = 'feedback.csv'
    file_exists = os.path.isfile(feedback_file)

    try:
        with open(feedback_file, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['input', 'query', 'feedback', 'comment']
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                quoting=csv.QUOTE_ALL,
                escapechar='\\',
            )

            if not file_exists:
                writer.writeheader()

            writer.writerow({
                'input': request.input,
                'query': request.query,
                'feedback': request.feedback,
                'comment': request.comment
            })
        return {"status": "Feedback received"}
    except Exception as e:
        print(f"Error writing feedback: {e}")
        return {"status": "Error processing feedback"}
