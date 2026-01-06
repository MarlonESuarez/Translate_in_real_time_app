from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    """Configuracion del servidor desde variables de entorno..."""

    #Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    #Model
    MODEL_PATH: str = "microsoft/VibeVoice-Realtime-0.5B"
    DEVICE: Literal["cuda", "mps", "cpu"] = "cpu"
    DEFAULT_VOICE: str = "en-Carter_man"

    #Performance Settings
    INFERENCE_STEPS: int = 5
    CFG_SCALE: float = 1.5

    # Google Cloud Translation
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Translation Settings
    DEFAULT_SOURCE_LANG: str = "es"
    DEFAULT_TARGET_LANG: str = "en"
    SUPPORTED_LANGUAGES: list = ["es", "en"]

    class Config:
        env_file = ".env"
        case_sensitive = True
    
# Instance global of settings
settings = Settings()