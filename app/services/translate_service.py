import os
import asyncio
from typing import Optional, Dict
from google.cloud import translate_v2 as translate
from app.config.settings import settings

class TranslateService:
    """
    Service for text translation using Google Cloud Translate API.

    Manages:
    - Translation client initialization
    - Language detection
    - Text translation
    - Language validation
    """

    def __init__(self):
        self.project_id = settings.GOOGLE_CLOUD_PROJECT_ID
        self.credentials_path = settings.GOOGLE_APPLICATION_CREDENTIALS
        self.supported_languages = settings.SUPPORTED_LANGUAGES
        self.client: Optional[translate.Client] = None

    async def load(self):
        """Initialize the Google Cloud Translate client."""
        print("Initializing Google Cloud Translate...")
        print(f"Project ID: {self.project_id}")

        # Handle credentials from environment variable (for Hugging Face Spaces)
        credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if credentials_json:
            import json
            import tempfile

            print("Found GOOGLE_APPLICATION_CREDENTIALS_JSON in environment")

            # Create temporary file with credentials
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(json.loads(credentials_json), f)
                temp_creds_path = f.name

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds_path
            print(f"Created temporary credentials file: {temp_creds_path}")

        # Set credentials if provided as file path
        elif self.credentials_path and os.path.exists(self.credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            print(f"Using credentials from: {self.credentials_path}")

        # Initialize client (synchronous, but fast)
        await asyncio.to_thread(self._load_sync)
        print("Google Cloud Translate initialized successfully")

    def _load_sync(self):
        """Synchronous client initialization."""
        try:
            self.client = translate.Client()

            # Test connection with a simple detection
            test_result = self.client.detect_language("test")
            print(f"Translation API test successful: {test_result}")
        except Exception as e:
            print(f"Warning: Could not initialize Google Translate: {e}")
            print("Translation features will be limited")
            # Don't raise - allow app to start even if translation fails

    def is_language_supported(self, lang_code: str) -> bool:
        """Check if a language code is supported."""
        return lang_code in self.supported_languages

    async def translate_text(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Translate text from source language to target language.

        Args:
            text: Text to translate
            target_lang: Target language code (e.g., 'en', 'es')
            source_lang: Source language code (optional, auto-detect if None)

        Returns:
            Dict with translation results including detected source language
        """
        if not self.client:
            raise RuntimeError("Translation client not initialized")

        # Validate languages
        if not self.is_language_supported(target_lang):
            raise ValueError(f"Target language '{target_lang}' not supported")

        if source_lang and not self.is_language_supported(source_lang):
            raise ValueError(f"Source language '{source_lang}' not supported")

        # Perform translation in thread (API is synchronous)
        result = await asyncio.to_thread(
            self._translate_sync,
            text,
            target_lang,
            source_lang
        )

        return result

    def _translate_sync(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> Dict[str, str]:
        """Synchronous translation."""

        # Translate
        result = self.client.translate(
            text,
            target_language=target_lang,
            source_language=source_lang
        )

        return {
            "original_text": text,
            "translated_text": result["translatedText"],
            "source_lang": source_lang or result.get("detectedSourceLanguage", "auto"),
            "target_lang": target_lang,
            "detected_source_lang": result.get("detectedSourceLanguage", source_lang)
        }

    async def detect_language(self, text: str) -> str:
        """Detect the language of the given text."""
        if not self.client:
            raise RuntimeError("Translation client not initialized")

        result = await asyncio.to_thread(
            lambda: self.client.detect_language(text)
        )

        return result["language"]

# Global instance
translate_service = TranslateService()
