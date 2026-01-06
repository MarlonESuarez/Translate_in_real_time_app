#!/bin/bash

# VibeVoice TTS Deployment Script for Google Cloud Run
# Usage: ./deploy.sh [PROJECT_ID] [REGION]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}VibeVoice TTS - Cloud Run Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get parameters or use defaults
PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null)}
REGION=${2:-us-central1}
SERVICE_NAME="vibevoice-tts"

# Validate PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: PROJECT_ID not set${NC}"
    echo "Usage: ./deploy.sh [PROJECT_ID] [REGION]"
    echo "Example: ./deploy.sh my-project-123 us-central1"
    exit 1
fi

echo -e "${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo ""

# Confirm deployment
read -p "Deploy to Cloud Run? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}Step 1: Setting up gcloud${NC}"
gcloud config set project $PROJECT_ID

echo ""
echo -e "${GREEN}Step 2: Enabling required APIs${NC}"
gcloud services enable cloudbuild.googleapis.com --quiet
gcloud services enable run.googleapis.com --quiet
gcloud services enable containerregistry.googleapis.com --quiet

echo ""
echo -e "${GREEN}Step 3: Deploying to Cloud Run${NC}"
echo -e "${YELLOW}This may take 10-20 minutes...${NC}"

gcloud run deploy $SERVICE_NAME \
  --source . \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=8Gi \
  --cpu=4 \
  --timeout=300 \
  --max-instances=10 \
  --min-instances=0 \
  --port=8080 \
  --set-env-vars="HOST=0.0.0.0,PORT=8080,DEVICE=cpu,MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B,DEFAULT_VOICE=en-Carter_man,INFERENCE_STEPS=5,CFG_SCALE=1.5"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Completed Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Service URL:${NC}"
echo "  $SERVICE_URL"
echo ""
echo -e "${YELLOW}WebSocket URL (for client):${NC}"
WS_URL=$(echo $SERVICE_URL | sed 's/https:/wss:/')
echo "  ${WS_URL}/tts/ws"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Update your React Native client with the WebSocket URL above"
echo "  2. Test the endpoint: curl $SERVICE_URL/health"
echo "  3. View logs: gcloud run services logs tail $SERVICE_NAME --region=$REGION"
echo ""
echo -e "${GREEN}Done!${NC}"
