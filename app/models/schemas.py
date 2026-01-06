from pydantic import BaseModel, Field
from typing import Optional, List

class TTSRequest(BaseModel):
    """Schema for TTS request payload."""

    text: str = Field(..., min_length=1, max_length=5000, description="The text to be converted to speech.")
    voice: Optional[str] = Field(None, description="The voice model to use for synthesis.")
    cfg_scale: Optional[float] = Field(1.5, ge=0.5, le=3.0, description="CFG scale for controlling creativity of the output.")
    inference_steps: Optional[int] = Field(5, ge=5, le=20, description="Number of inference steps for generation.")

class TranslateRequest(BaseModel):
    """Schema for translation request payload."""

    text: str = Field(..., min_length=1, max_length=5000, description="Text to translate")
    source_lang: str = Field("es", description="Source language code (ISO 639-1)")
    target_lang: str = Field("en", description="Target language code (ISO 639-1)")

class TranslateResponse(BaseModel):
    """Schema for translation response."""

    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    detected_source_lang: Optional[str] = None

class TranslateTTSRequest(BaseModel):
    """Schema for combined translation + TTS via WebSocket."""

    text: str = Field(..., min_length=1, max_length=5000, description="Text to translate and speak")
    source_lang: str = Field("es", description="Source language code")
    target_lang: str = Field("en", description="Target language code")
    voice: Optional[str] = Field(None, description="Voice for TTS (language-appropriate)")
    cfg_scale: Optional[float] = Field(1.5, ge=0.5, le=3.0, description="CFG scale")
    inference_steps: Optional[int] = Field(5, ge=5, le=20, description="Inference steps")

class SupportedLanguagesResponse(BaseModel):
    """Schema for supported languages list."""

    languages: List[str]
    default_source: str
    default_target: str

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