from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.models.schemas import TTSRequest, VoiceListResponse
from app.services.tts_service import tts_service
import json
router = APIRouter(prefix="/tts", tags=["TTS"])

@router.get("/voices", response_model=VoiceListResponse)
async def list_voices():
    """Endpoint to list available TTS voices."""
    
    return VoiceListResponse(
        voices=list(tts_service.voice_presets.keys()),
        default_voice=tts_service.default_voice_key,
        total=len(tts_service.voice_presets)
    )

@router.websocket("/ws")
async def websocket_tts(websocket: WebSocket):
    """WebSocket endpoint for real-time TTS synthesis."""
    
    await websocket.accept()
    
    try:
        # Receive TTS request parameters
        data = await websocket.receive_json()

        text = data.get("text", "")
        voice = data.get("voice")
        cfg = float(data.get("cfg", 1.5))
        steps = int(data.get("steps", 5))

        if not text:
            await websocket.send_json({
                  "type": "error",
                  "message": "No text provided"
              })
            return
        
        # log init
        await websocket.send_json({
            "type": "status",
            "message": "Generating audio...",
            "text_length": len(text),
            "voice": voice or tts_service.default_voice_key,
        })

        # generate and send audio chunks
        chunk_count = 0
        async for audio_chunk in tts_service.generate_stream(
            text=text,
            voice_key=voice,
            cfg_scale=cfg,
            inference_steps=steps
        ):
            await websocket.send_bytes(audio_chunk)
            chunk_count += 1

        # completion message
        await websocket.send_json({
            "type": "complete",
            "chunks_sent": chunk_count
        })
    
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        error_msg = str(e)
        print(f"Error during TTS processing: {error_msg}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": error_msg
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass