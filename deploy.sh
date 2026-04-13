#!/bin/bash
# Deploy ReelSearch transcription service to Cloud Run
# Usage: ./deploy.sh

set -e

PROJECT_ID="project-311d8990-533c-4b37-96b"
REGION="us-central1"
SERVICE="transcription-service"
IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/reelsearch/$SERVICE:latest"

# Load env vars from .env
source .env

echo "=== Building and pushing image ==="
gcloud builds submit --tag "$IMAGE"

echo "=== Deploying to Cloud Run ==="
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 3001 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "SUPABASE_URL=$SUPABASE_URL,SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY,INSTAGRAM_COOKIES_FILE=/tmp/cookies.txt" \
  --set-secrets "/tmp/cookies.txt=INSTAGRAM_COOKIES:latest"

echo ""
echo "=== Deployed ==="
gcloud run services describe "$SERVICE" --region "$REGION" --format "value(status.url)"
