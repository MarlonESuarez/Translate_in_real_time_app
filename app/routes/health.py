from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.tts_service import tts_service

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify service status."""

    return HealthResponse(
        status="healthy" if tts_service.model else "loading",
        model_loaded=tts_service.model is not None,
        device=tts_service.device,
        available_voices=len(tts_service.voice_presets)
    )