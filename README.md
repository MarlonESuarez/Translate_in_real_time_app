---
title: VibeVoice Real-Time Translation
emoji: 🗣️
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
app_port: 8080
---

# VibeVoice Real-Time Translation API

Real-time speech translation API with Text-to-Speech using Microsoft VibeVoice-Realtime-0.5B model.

## Features

- Real-time translation via WebSocket
- Text-to-Speech generation with VibeVoice
- Streaming audio output (PCM16 format)
- REST API for single translations
- Health check endpoint

## API Endpoints

### WebSocket Translation
```
ws://[your-space-url]/api/translate/ws
```

Send JSON:
```json
{
  "text": "Hola, cómo estás?",
  "source_lang": "es",
  "target_lang": "en",
  "cfg": 1.5,
  "steps": 5
}
```

Receive:
```json
{
  "type": "translation",
  "text": "Hello, how are you?"
}
{
  "type": "audio_chunk",
  "audio": "base64_encoded_pcm16_data"
}
{
  "type": "done"
}
```

### REST API
```bash
POST /api/translate/text
Content-Type: application/json

{
  "text": "Hola mundo",
  "source_lang": "es",
  "target_lang": "en",
  "cfg": 1.5,
  "steps": 5
}
```

### Health Check
```
GET /health
```

## Technical Details

- **Model**: microsoft/VibeVoice-Realtime-0.5B
- **Translation**: Google Cloud Translation API
- **Audio Format**: PCM16, 24000Hz, mono
- **Framework**: FastAPI
- **Runtime**: Python 3.11
