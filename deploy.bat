@echo off
REM VibeVoice TTS Deployment Script for Google Cloud Run (Windows)
REM Usage: deploy.bat [PROJECT_ID] [REGION]

echo ========================================
echo VibeVoice TTS - Cloud Run Deployment
echo ========================================
echo.

REM Get parameters or use defaults
set PROJECT_ID=%1
set REGION=%2

if "%PROJECT_ID%"=="" (
    for /f "tokens=*" %%i in ('gcloud config get-value project 2^>nul') do set PROJECT_ID=%%i
)

if "%REGION%"=="" set REGION=us-central1

set SERVICE_NAME=vibevoice-tts

REM Validate PROJECT_ID
if "%PROJECT_ID%"=="" (
    echo Error: PROJECT_ID not set
    echo Usage: deploy.bat [PROJECT_ID] [REGION]
    echo Example: deploy.bat my-project-123 us-central1
    exit /b 1
)

echo Configuration:
echo   Project ID: %PROJECT_ID%
echo   Region: %REGION%
echo   Service Name: %SERVICE_NAME%
echo.

REM Confirm deployment
set /p CONFIRM="Deploy to Cloud Run? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Deployment cancelled
    exit /b 0
)

echo.
echo Step 1: Setting up gcloud
gcloud config set project %PROJECT_ID%

echo.
echo Step 2: Enabling required APIs
gcloud services enable cloudbuild.googleapis.com --quiet
gcloud services enable run.googleapis.com --quiet
gcloud services enable containerregistry.googleapis.com --quiet

echo.
echo Step 3: Deploying to Cloud Run
echo This may take 10-20 minutes...

gcloud run deploy %SERVICE_NAME% ^
  --source . ^
  --region=%REGION% ^
  --platform=managed ^
  --allow-unauthenticated ^
  --memory=8Gi ^
  --cpu=4 ^
  --timeout=300 ^
  --max-instances=10 ^
  --min-instances=0 ^
  --port=8080 ^
  --set-env-vars="HOST=0.0.0.0,PORT=8080,DEVICE=cpu,MODEL_PATH=microsoft/VibeVoice-Realtime-0.5B,DEFAULT_VOICE=en-Carter_man,INFERENCE_STEPS=5,CFG_SCALE=1.5"

REM Get service URL
for /f "tokens=*" %%i in ('gcloud run services describe %SERVICE_NAME% --region=%REGION% --format="value(status.url)"') do set SERVICE_URL=%%i

echo.
echo ========================================
echo Deployment Completed Successfully!
echo ========================================
echo.
echo Service URL:
echo   %SERVICE_URL%
echo.
echo WebSocket URL (for client):
set WS_URL=%SERVICE_URL:https:=wss:%
echo   %WS_URL%/tts/ws
echo.
echo Next Steps:
echo   1. Update your React Native client with the WebSocket URL above
echo   2. Test the endpoint: curl %SERVICE_URL%/health
echo   3. View logs: gcloud run services logs tail %SERVICE_NAME% --region=%REGION%
echo.
echo Done!
