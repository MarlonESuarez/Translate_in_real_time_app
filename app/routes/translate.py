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


@router.websocket("/ws")
async def websocket_translate_tts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time continuous translation + TTS.

    Flow (continuous mode):
    1. Accept connection
    2. Loop: receive text + translate + generate TTS + stream audio
    3. Keep connection open for multiple translations
    4. Close only when client disconnects
    """

    await websocket.accept()
    print("🔌 Translation WebSocket connected - continuous mode")

    try:
        # Continuous loop for multiple translations
        while True:
            # Receive translation + TTS request
            data = await websocket.receive_json()

            # Generate unique ID for this translation
            translation_id = str(uuid.uuid4())[:8]

            text = data.get("text", "")
            source_lang = data.get("source_lang", "es")
            target_lang = data.get("target_lang", "en")
            voice = data.get("voice")
            cfg = float(data.get("cfg", 1.5))
            steps = int(data.get("steps", 5))

            if not text:
                await websocket.send_json({
                    "type": "error",
                    "message": "No text provided",
                    "translation_id": translation_id
                })
                continue  # Skip this iteration, wait for next message

            print(f"📝 [{translation_id}] Received text to translate: {text}")

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

            print(f"✅ [{translation_id}] Translation cycle complete, ready for next message")

    except WebSocketDisconnect:
        print("🔌 Client disconnected from translation WebSocket")
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        print(error_msg)
        try:
            # Try to send error with translation_id if available
            error_data = {"type": "error", "message": error_msg}
            if 'translation_id' in locals():
                error_data["translation_id"] = translation_id
            await websocket.send_json(error_data)
        except:
            pass
    except Exception as e:
        error_msg = str(e)
        print(f"Error during translation/TTS processing: {error_msg}")
        try:
            # Try to send error with translation_id if available
            error_data = {"type": "error", "message": error_msg}
            if 'translation_id' in locals():
                error_data["translation_id"] = translation_id
            await websocket.send_json(error_data)
        except:
            pass
    finally:
        print("🔌 Closing translation WebSocket connection")
        try:
            await websocket.close()
        except:
            pass
