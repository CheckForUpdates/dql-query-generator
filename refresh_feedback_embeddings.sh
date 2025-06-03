#!/bin/bash

set -e

echo "🔄 Rebuilding feedback-based embeddings..."

echo "📥 Converting feedback to embedding JSON..."
python3 backend/convert_feedback_to_embeddings.py

echo "🧠 Generating all embeddings..."
mkdir -p logs
python3 backend/generate_embeddings.py > logs/generate.log 2>&1

echo "🚀 Uploading to Elasticsearch..."
python3 backend/upload_to_elasticsearch.py

echo "✅ Feedback embeddings updated."
