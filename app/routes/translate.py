from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.models.schemas import (
    TranslateRequest,
    TranslateResponse,
    TranslateTTSRequest,
    SupportedLanguagesResponse
)
from app.services.translate_service import translate_service
from app.services.tts_service import tts_service
import json
import uuid
import asyncio

router = APIRouter(prefix="/translate", tags=["Translation"])


@router.get("/languages", response_model=SupportedLanguagesResponse)
async def list_supported_languages():
    """Endpoint to list supported translation languages."""

    return SupportedLanguagesResponse(
        languages=translate_service.supported_languages,
        default_source=translate_service.supported_languages[0] if translate_service.supported_languages else "es",
        default_target=translate_service.supported_languages[1] if len(translate_service.supported_languages) > 1 else "en"
    )


@router.post("/", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """REST endpoint for text translation (no TTS)."""

    try:
        result = await translate_service.translate_text(
            text=request.text,
            target_lang=request.target_lang,
            source_lang=request.source_lang
        )

        return TranslateResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")


async def handle_translation_request(
    websocket: WebSocket,
    data: dict,
    translation_id: str
):
    """
    Handle a single translation request asynchronously.
    This allows multiple translations to be processed in parallel.
    """
    try:
        text = data.get("text", "")
        source_lang = data.get("source_lang", "es")
        target_lang = data.get("target_lang", "en")
        voice = data.get("voice")
        cfg = float(data.get("cfg", 1.5))
        steps = int(data.get("steps", 3))  # Reduced default from 5 to 3

        if not text:
            await websocket.send_json({
                "type": "error",
                "message": "No text provided",
                "translation_id": translation_id
            })
            return

        print(f"📝 [{translation_id}] Processing translation request: {text}")

        # Step 1: Translate
        await websocket.send_json({
            "type": "status",
            "message": "Translating...",
            "stage": "translation",
            "translation_id": translation_id
        })

        translation_result = await translate_service.translate_text(
            text=text,
            target_lang=target_lang,
            source_lang=source_lang
        )

        translated_text = translation_result["translated_text"]
        print(f"✅ [{translation_id}] Translated: {translated_text}")

        # Send translation result
        await websocket.send_json({
            "type": "translation_complete",
            "translation_id": translation_id,
            "original_text": text,
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "detected_source_lang": translation_result.get("detected_source_lang")
        })

        # Step 2: Generate TTS for translated text
        await websocket.send_json({
            "type": "status",
            "message": "Generating speech...",
            "stage": "tts",
            "text_length": len(translated_text),
            "voice": voice or tts_service.default_voice_key,
            "translation_id": translation_id
        })

        # Select appropriate voice based on target language if not specified
        if not voice:
            # Map language to default voice
            voice_map = {
                "en": "en-Carter_man",
                "es": "sp-Spk1_man"
            }
            voice = voice_map.get(target_lang, tts_service.default_voice_key)

        # Signal start of audio chunks for this translation
        await websocket.send_json({
            "type": "audio_start",
            "translation_id": translation_id
        })

        # Generate and stream audio chunks
        chunk_count = 0
        async for audio_chunk in tts_service.generate_stream(
            text=translated_text,
            voice_key=voice,
            cfg_scale=cfg,
            inference_steps=steps
        ):
            await websocket.send_bytes(audio_chunk)
            chunk_count += 1

        print(f"🔊 [{translation_id}] Sent {chunk_count} audio chunks")

        # Completion message
        await websocket.send_json({
            "type": "complete",
            "translation_id": translation_id,
            "chunks_sent": chunk_count,
            "translation": translated_text
        })

        print(f"✅ [{translation_id}] Translation cycle complete")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ [{translation_id}] Error: {error_msg}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": error_msg,
                "translation_id": translation_id
            })
        except:
            pass


@router.websocket("/ws")
async def websocket_translate_tts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time continuous translation + TTS with parallel processing.

    Flow (parallel mode):
    1. Accept connection
    2. Loop: receive requests and spawn parallel tasks
    3. Each translation runs independently without blocking others
    4. Close only when client disconnects
    """

    await websocket.accept()
    print("🔌 Translation WebSocket connected - parallel processing mode")

    # Track active tasks
    active_tasks = set()

    try:
        # Continuous loop for multiple translations
        while True:
            # Receive translation + TTS request
            data = await websocket.receive_json()

            # Generate unique ID for this translation
            translation_id = str(uuid.uuid4())[:8]

            # Create task for this translation (runs in parallel)
            task = asyncio.create_task(
                handle_translation_request(websocket, data, translation_id)
            )

            # Track task
            active_tasks.add(task)
            task.add_done_callback(active_tasks.discard)

            print(f"🚀 [{translation_id}] Task created (active tasks: {len(active_tasks)})")

    except WebSocketDisconnect:
        print("🔌 Client disconnected from translation WebSocket")

        # Wait for all active tasks to complete
        if active_tasks:
            print(f"⏳ Waiting for {len(active_tasks)} active tasks to complete...")
            await asyncio.gather(*active_tasks, return_exceptions=True)
            print("✅ All tasks completed")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ WebSocket error: {error_msg}")

        # Cancel all active tasks
        if active_tasks:
            print(f"🛑 Cancelling {len(active_tasks)} active tasks...")
            for task in active_tasks:
                task.cancel()
            await asyncio.gather(*active_tasks, return_exceptions=True)

    finally:
        print("🔌 Closing translation WebSocket connection")
        try:
            await websocket.close()
        except:
            pass
