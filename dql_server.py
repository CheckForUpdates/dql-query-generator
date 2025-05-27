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
    comment: str = ""  # Optional comment

@app.get("/")
def read_root():
    return {"message": "running..."}

@app.post("/generate")
def generate(request: QueryRequest):
    dql, timestamp = generate_dql(request.query)
    # Format timestamp to MM/dd/yyyy H:M a
    try:
        dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
    except Exception:
        dt = datetime.datetime.now()
    formatted_timestamp = dt.strftime("%m/%d/%Y %I:%M %p")
    return { "dql": dql, "timestamp": formatted_timestamp }

@app.post("/feedback")
def receive_feedback(request: FeedbackRequest):
    feedback_file = 'feedback.csv'
    file_exists = os.path.isfile(feedback_file)

    try:
        with open(feedback_file, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'input', 'query', 'feedback', 'received_at', 'comment']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader() # Write header only if file is new

            # Format received_at to MM/dd/yyyy H:M a
            received_at = datetime.datetime.now().strftime("%m/%d/%Y %I:%M %p")
            writer.writerow({
                'timestamp': request.timestamp,
                'input': request.input,
                'query': request.query,
                'feedback': request.feedback,
                'received_at': received_at,
                'comment': request.comment
            })
        return {"status": "Feedback received"}
    except Exception as e:
        print(f"Error writing feedback: {e}")
        # Consider raising HTTPException for client feedback
        return {"status": "Error processing feedback"}
