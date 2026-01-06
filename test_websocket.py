import asyncio
import websockets
import json
import struct
import wave

async def test_tts():
    """Probar el WebSocket TTS y guardar el audio"""

    uri = "ws://localhost:8000/tts/ws"

    print("🔌 Conectando al servidor...")

    try:
          # Increase timeout for CPU generation (can take 30-60 seconds)
          async with websockets.connect(uri, ping_interval=60, ping_timeout=60, close_timeout=60) as websocket:
              print("✅ Conectado!")

              # Configuración de la petición
              request = {
                  "text": "Hello world, dejame decirte que Venegas Paez es Peta.",
                  "voice": "sp-Spk1_man",
                  "cfg": 1.5,
                  "steps": 5
              }

              print(f"\n📤 Enviando texto: '{request['text']}'")
              print(f"🎙️  Voz: {request['voice']}" )
              print(f"⚙️  CFG: {request['cfg']}, Steps: {request['steps']}")
              print("\n⏳ Generando audio... (en CPU esto toma ~3-8 segundos)\n")

              # Enviar petición
              await websocket.send(json.dumps(request))

              # Recibir respuestas
              audio_chunks = []
              chunk_count = 0

              while True:
                  message = await websocket.recv()

                  # Mensaje JSON (status)
                  if isinstance(message, str):
                      data = json.loads(message)
                      msg_type = data.get("type")

                      if msg_type == "status":
                          print(f"📊 {data.get('message')}")

                      elif msg_type == "complete":
                          print(f"\n✅ Generación completada!")
                          print(f"📦 Chunks recibidos: {data.get('chunks_sent')}")
                          break

                      elif msg_type == "error":
                          print(f"\n❌ Error: {data.get('message')}")
                          return

                  # Mensaje binario (audio)
                  else:
                      chunk_count += 1
                      audio_chunks.append(message)
                      print(f"🔊 Chunk #{chunk_count}: {len(message)} bytes", end='\r')

              # Guardar audio en archivo WAV
              if audio_chunks:
                  output_file = "output_test.wav"
                  print(f"\n💾 Guardando audio en: {output_file}")

                  # Combinar todos los chunks
                  audio_data = b''.join(audio_chunks)

                  # Crear archivo WAV
                  with wave.open(output_file, 'wb') as wav_file:
                      wav_file.setnchannels(1)  # Mono
                      wav_file.setsampwidth(2)  # 16-bit (2 bytes)
                      wav_file.setframerate(24000)  # 24kHz
                      wav_file.writeframes(audio_data)

                  print(f"✅ Audio guardado exitosamente!")
                  print(f"📁 Ubicación: {output_file}")
                  print(f"📊 Tamaño: {len(audio_data)} bytes ({len(audio_data)/1024:.1f} KB)")
                  print(f"⏱️  Duración: ~{len(audio_data)/(24000*2):.1f} segundos")
                  print("\n🎧 Reproduce el archivo para escuchar el resultado!")

    except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError):
          print("❌ Error: No se pudo conectar al servidor")
          print("   Verifica que el servidor esté corriendo en http://localhost:8000")
    except Exception as e:
          print(f"❌ Error inesperado: {e}")
          import traceback
          traceback.print_exc()

if __name__ == "__main__":
      print("=" * 60)
      print("🧪 Test de VibeVoice WebSocket TTS")
      print("=" * 60)

      asyncio.run(test_tts())

      print("\n" + "=" * 60)
      print("✅ Test completado!")
      print("=" * 60)