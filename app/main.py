from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config.settings import settings
from app.services.tts_service import tts_service
from app.services.translate_service import translate_service
from app.routes import health, tts, translate

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle del servidor
    - Startup: Cargar modelo VibeVoice
    - Shutdown: Limpieza
    """
    # Startup
    print("=" * 60)
    print("Iniciando VibeVoice TTS Backend...")
    print("=" * 60)

    try:
        await tts_service.load()
        await translate_service.load()
        print("=" * 60)
        print("Servidor listo para recibir peticiones!")
        print(f"Device: {settings.DEVICE}")
        print(f" Voces disponibles: { len(tts_service.voice_presets)}")
        print(f"Voz por defecto: {tts_service.default_voice_key}")
        print(f"Translation enabled: {translate_service.client is not None}")
        print(f"Supported languages: {', '.join(translate_service.supported_languages)}")
        print("=" * 60)
    except Exception as e:
        print("=" * 60)
        print(f"Error al cargar el modelo: {e}")
        print("=" * 60)
        raise

    yield

    # Shutdown
    print("👋 Cerrando servidor...")

# Crear aplicación FastAPI
app = FastAPI(
    title="VibeVoice TTS API",
    description="API REST y WebSocket para Text-to-Speech con VibeVoice de Microsoft",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - Permitir peticiones desde React Native y otros clientes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: especificar orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(health.router)
app.include_router(tts.router)
app.include_router(translate.router)

# Endpoint raíz
@app.get("/")
async def root():
    """
    Endpoint raíz - Información de la API
    """
    return {
        "message": "VibeVoice TTS API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "voices": "/tts/voices",
            "websocket": "/tts/ws",
            "translate": "/translate/",
            "translate_languages": "/translate/languages",
            "translate_websocket": "/translate/ws"
        }
    }

@app.get("/docs-info")
async def docs_info():
    """
      Información sobre cómo usar la API
    """
    return {
        "swagger_ui": "http://localhost:8000/docs",
        "redoc": "http://localhost:8000/redoc",
        "websocket_endpoint": "ws://localhost:8000/tts/ws",
        "example_request": {
            "text": "Hello world, this is a test",
            "voice": "en-Carter_man",
            "cfg": 1.5,
            "steps": 5
        }
    }