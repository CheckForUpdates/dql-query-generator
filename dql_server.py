# dql_server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dql_logic import generate_dql
import datetime # Added for timestamp in feedback
import csv # Added for logging feedback
import os # Added for checking file existence

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

class FeedbackRequest(BaseModel):
    input: str
    query: str
    timestamp: str
    feedback: str # 'good' or 'bad'

@app.get("/")
def read_root():
    return {"message": "running..."}

@app.post("/generate")
def generate(request: QueryRequest):
    dql, timestamp = generate_dql(request.query)
    return { "dql": dql, "timestamp": timestamp }

@app.post("/feedback")
def receive_feedback(request: FeedbackRequest):
    feedback_file = 'feedback.csv'
    file_exists = os.path.isfile(feedback_file)

    try:
        with open(feedback_file, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'input', 'query', 'feedback', 'received_at']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader() # Write header only if file is new

            writer.writerow({
                'timestamp': request.timestamp,
                'input': request.input,
                'query': request.query,
                'feedback': request.feedback,
                'received_at': datetime.datetime.now().isoformat()
            })
        return {"status": "Feedback received"}
    except Exception as e:
        print(f"Error writing feedback: {e}")
        # Consider raising HTTPException for client feedback
        return {"status": "Error processing feedback"}
