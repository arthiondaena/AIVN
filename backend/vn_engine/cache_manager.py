import hashlib
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_dir: str = "cache/audio"):
        self.cache_dir = Path(cache_dir)
        self.ensure_cache_dir()

    def ensure_cache_dir(self):
        """Ensure the cache directory exists."""
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_hash(self, text: str, voice_name: str, style_prompt: str = "") -> str:
        """Generate a SHA256 hash based on input parameters."""
        # Normalize inputs to ensure consistent hashing
        data_string = f"{text.strip()}|{voice_name.strip()}|{style_prompt.strip()}"
        return hashlib.sha256(data_string.encode('utf-8')).hexdigest()

    def get_cache_path(self, text: str, voice_name: str, style_prompt: str = "") -> Path:
        """Return the expected filesystem path for the audio file."""
        file_hash = self._generate_hash(text, voice_name, style_prompt)
        return self.cache_dir / f"{file_hash}.wav"

    def exists(self, path: Path) -> bool:
        """Check if the cache file exists."""
        return path.exists() and path.stat().st_size > 0

    def save_audio(self, path: Path, audio_data: bytes):
        """Save audio bytes to the specified path."""
        try:
            with open(path, "wb") as f:
                f.write(audio_data)
            logger.info(f"Saved audio to cache: {path}")
        except Exception as e:
            logger.error(f"Failed to save audio to cache {path}: {e}")
            # Attempt cleanup if partial write
            if path.exists():
                try:
                    os.remove(path)
                except:
                    pass
