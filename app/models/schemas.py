from pydantic import BaseModel, Field
from typing import Optional, List

class TTSRequest(BaseModel):
    """Schema for TTS request payload."""

    text: str = Field(..., min_length=1, max_length=5000, description="The text to be converted to speech.")
    voice: Optional[str] = Field(None, description="The voice model to use for synthesis.")
    cfg_scale: Optional[float] = Field(1.5, ge=0.5, le=3.0, description="CFG scale for controlling creativity of the output.")
    inference_steps: Optional[int] = Field(5, ge=5, le=20, description="Number of inference steps for generation.")

class VoiceInfo(BaseModel):
    """Schema for voice information."""

    name: str
    path: str

class VoiceListResponse(BaseModel):
    """Schema for the response containing a list of available voices."""

    voices: List[str]
    default_voice: str
    total: int

class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    model_loaded: bool
    device: str
    available_voices: int