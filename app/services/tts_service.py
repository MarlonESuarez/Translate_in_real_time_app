import torch
import numpy as np
import os
from pathlib import Path
from typing import AsyncIterator, Optional, Dict
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

from vibevoice import (
    VibeVoiceStreamingForConditionalGenerationInference,
    VibeVoiceStreamingProcessor
)
from vibevoice.modular.streamer import AudioStreamer

from app.config.settings import settings

class TTSService:
    """
      Service for Text-to-Speech with VibeVoice.

      Manages:
      - Model loading
      - Voice presets management
      - Streaming audio generation
    """
     
    def __init__(self):
          self.model_path = settings.MODEL_PATH
          self.device = settings.DEVICE
          self.model: Optional[VibeVoiceStreamingForConditionalGenerationInference] = None
          self.processor: Optional[VibeVoiceStreamingProcessor] = None
          self.voice_presets: Dict[str, Path] = {}
          self.voice_cache: Dict[str, any] = {}  # Cache for loaded voice presets
          self.default_voice_key = settings.DEFAULT_VOICE
          self.sample_rate = 24000
          self._executor = ThreadPoolExecutor(max_workers=3)  # Increased from 1 to 3
          self._generation_lock = threading.Lock()  # Lock to serialize model.generate() calls
    
    async def load(self):
            """Load the TTS model and voice presets."""
            print("Loading TTS model...")
            print(f"Using device: {self.device}")
            await asyncio.to_thread(self._load_sync)
            print("TTS model loaded.")
    
    def _load_sync(self):
            """Synchronous model loading."""
            # Get HuggingFace token from environment
            hf_token = os.getenv("HF_TOKEN")

            # Determine device
            if self.device == "cuda":
                dtype = torch.float16
                attn = "flash_attention_2"
            elif self.device == "mps":
                dtype = torch.float32
                attn = "sdpa"
            else:
                dtype = torch.float32
                attn = "sdpa"

            print(f"Loading model from {self.model_path} with dtype {dtype} and attention {attn}")
            self.processor = VibeVoiceStreamingProcessor.from_pretrained(
                self.model_path,
                token=hf_token
            )

            # Load model
            print("Loading model weights...")
            try:
                self.model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                    self.model_path,
                    torch_dtype=dtype,
                    device_map=self.device,
                    attn_implementation=attn,
                    token=hf_token
                )
                print("Model weights loaded successfully.")
            except Exception as e:
                if attn == "flash_attention_2":
                    print("Flash Attention 2 failed, retrying with SDPA...")
                    self.model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                        self.model_path,
                        torch_dtype=dtype,
                        device_map=self.device,
                        attn_implementation="sdpa",
                        token=hf_token
                    )
                    print("Model weights loaded successfully with SDPA.")
                else:
                     raise e
            
            self.model.eval()

            #configure noice schedulers
            self.model.model.noise_scheduler = self.model.model.noise_scheduler.from_config(
                self.model.model.noise_scheduler.config,
                algorithm_type="sde-dpmsolver++",
                beta_schedule="squaredcos_cap_v2"
            )

            # Load voice presets
            self._load_voice_presets()
        
    def _load_voice_presets(self):
            """Load voice presets from the model directory."""
            voices_dir = Path("voices/streaming_model")

            if not voices_dir.exists():
                raise RuntimeError(f"Voices directory not found: {voices_dir}")

            for pt_file in voices_dir.glob("*.pt"):
                voice_name = pt_file.stem
                self.voice_presets[voice_name] = pt_file

            if not self.voice_presets:
                raise RuntimeError("No voice presets found.")

            # verify default voice
            if self.default_voice_key not in self.voice_presets:
                self.default_voice_key = list(self.voice_presets.keys())[0]
                print(f"Default voice not found. Using {self.default_voice_key} as default.")

            # Pre-cache most commonly used voices to reduce latency
            common_voices = ["en-Carter_man", "sp-Spk1_man", "en-Emma_woman", "sp-Spk0_woman"]
            print("Pre-caching common voice presets...")
            for voice_key in common_voices:
                if voice_key in self.voice_presets:
                    try:
                        voice_path = self.voice_presets[voice_key]
                        cached_prompt = torch.load(
                            voice_path,
                            map_location=self.device,
                            weights_only=False
                        )
                        self.voice_cache[voice_key] = cached_prompt
                        print(f"  ✓ Cached voice preset: {voice_key}")
                    except Exception as e:
                        print(f"  ✗ Failed to cache {voice_key}: {e}")
            print(f"Voice cache ready with {len(self.voice_cache)} presets")
    
    async def generate_stream(
        self,
        text: str,
        voice_key: Optional[str] = None,
        cfg_scale: float = 1.5,
        inference_steps: int = 5
    ) -> AsyncIterator[bytes]:
        """Generate audio stream asynchronously."""
        
        # select voice
        voice = voice_key if voice_key in self.voice_presets else self.default_voice_key

        print(f"Generating audio with voice: {voice}")

        # Try to use cached voice preset, otherwise load from disk
        if voice in self.voice_cache:
            print(f"  ✓ Using cached voice preset: {voice}")
            prefilled_outputs = self.voice_cache[voice]
        else:
            print(f"  ⚠ Voice not cached, loading from disk: {voice}")
            voice_path = self.voice_presets[voice]
            # Note: weights_only=False is required because voice presets contain model objects
            # These files come from Microsoft's official VibeVoice repo and are trusted
            prefilled_outputs = await asyncio.to_thread(
                lambda: torch.load(voice_path, map_location=self.device, weights_only=False)
            )
            # Cache it for next time
            self.voice_cache[voice] = prefilled_outputs
            print(f"  ✓ Cached voice preset for future use: {voice}")

        # prepare inputs
        inputs =  self.processor.process_input_with_cached_prompt(
            text=text,
            cached_prompt=prefilled_outputs,
            padding=True,
            return_tensors="pt",
            return_attention_mask=True
        )
        print("Inputs prepared for generation.")
        # move to device
        inputs = {
             k: v.to(self.device) if hasattr(v, "to") else v
             for k, v in inputs.items()
        }
        print("Inputs moved to device.")
        # configure streaming
        audio_streamer = AudioStreamer(
             batch_size=1
        )

        # Generate in thread separately (using threading.Thread like official demo)
        import copy

        errors = []

        def run_generation_sync():
            try:
                print("Starting model.generate() in thread...")

                # CRITICAL: Use lock to serialize model access
                # The noise_scheduler has internal state that is NOT thread-safe
                with self._generation_lock:
                    print("Acquired generation lock, configuring scheduler...")
                    self.model.set_ddpm_inference_steps(num_steps=inference_steps)
                    print(f"DDPM inference steps set to {inference_steps}.")

                    result = self.model.generate(
                        **inputs,
                        max_new_tokens=None,
                        cfg_scale=cfg_scale,
                        tokenizer=self.processor.tokenizer,
                        generation_config={
                            'do_sample': False,
                            'temperature': 1.0,
                            'top_p': 1.0
                        },
                        audio_streamer=audio_streamer,
                        verbose=True,
                        refresh_negative=True,
                        all_prefilled_outputs=copy.deepcopy(prefilled_outputs)
                    )
                    print(f"Generation completed successfully, releasing lock")
                return result
            except Exception as e:
                print(f"ERROR in generation thread: {e}")
                import traceback
                traceback.print_exc()
                errors.append(e)
                audio_streamer.end()

        thread = threading.Thread(target=run_generation_sync, daemon=True)
        thread.start()
        print("Generation thread started.")

        # Stream audio chunks
        try:
            stream = audio_streamer.get_stream(0)
            chunk_num = 0
            print("Starting audio streaming...")
            print(f"stream: {stream}")
            for audio_chunk in stream:
                print(f"Streaming chunk {chunk_num}...")
                # Convert to numpy
                if torch.is_tensor(audio_chunk):
                    audio_chunk = audio_chunk.cpu().to(torch.float32).numpy()
                else:
                    audio_chunk = np.array(audio_chunk, dtype=np.float32)

                print(f"  Raw chunk shape: {audio_chunk.shape}, size: {audio_chunk.size}")

                # Nomalize
                if audio_chunk.ndim > 1:
                    print(f"  Multi-dimensional, averaging...")
                    audio_chunk = audio_chunk.reshape(-1)

                print(f"  After reshape: {audio_chunk.shape}, size: {audio_chunk.size}")

                peak = np.max(np.abs(audio_chunk)) if audio_chunk.size else 0.0
                if peak > 1.0:
                    audio_chunk = audio_chunk / peak

                # convert to PCM16
                pcm16 = (np.clip(audio_chunk, -1.0, 1.0) * 32767.0).astype(np.int16)

                print(f"  PCM16 size: {len(pcm16.tobytes())} bytes")

                chunk_num += 1
                yield pcm16.tobytes()
        
            print(f"✓ Generated {chunk_num} audio chunks")

        finally:
            audio_streamer.end()
            # Wait for thread to finish
            await asyncio.to_thread(thread.join)

            # Check for errors
            if errors:
                raise errors[0]

# Instance global of TTSService
tts_service = TTSService()
        