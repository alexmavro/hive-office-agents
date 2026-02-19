"""Voice transcription provider using Gemini multimodal API."""

import base64
import os
from pathlib import Path

import httpx
from loguru import logger


_MIME_MAP = {
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
}

# Gemini Flash 2.0 — fast, cheap, handles audio well
_TRANSCRIPTION_MODEL = "gemini-2.0-flash"


class GeminiTranscriptionProvider:
    """
    Voice transcription via the Gemini multimodal API.

    Sends the audio file as base64 inline data and asks Gemini to transcribe it.
    Supports OGG (Telegram voice), MP3, WAV, M4A, FLAC.
    Uses gemini-2.0-flash for speed and cost efficiency.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        self._base_url = (
            "https://generativelanguage.googleapis.com/v1beta/models"
            f"/{_TRANSCRIPTION_MODEL}:generateContent"
        )

    async def transcribe(self, file_path: str | Path) -> str:
        """
        Transcribe an audio file using Gemini.

        Args:
            file_path: Path to the audio file.

        Returns:
            Transcribed text, or empty string on failure.
        """
        if not self.api_key:
            logger.warning("Gemini API key not configured — cannot transcribe audio")
            return ""

        path = Path(file_path)
        if not path.exists():
            logger.error(f"Audio file not found: {file_path}")
            return ""

        mime_type = _MIME_MAP.get(path.suffix.lower(), "audio/ogg")
        audio_b64 = base64.b64encode(path.read_bytes()).decode()

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Transcribe this voice message accurately. "
                                "Return only the transcription text, nothing else."
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": audio_b64,
                            }
                        },
                    ]
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    self._base_url,
                    params={"key": self.api_key},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                return text
        except Exception as e:
            logger.error(f"Gemini transcription error: {e}")
            return ""


# Backward-compat alias — any code still importing GroqTranscriptionProvider still works
GroqTranscriptionProvider = GeminiTranscriptionProvider
