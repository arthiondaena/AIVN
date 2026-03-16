import os
from google.oauth2 import service_account
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='allow')
    GOOGLE_APPLICATION_CREDENTIALS: str = None
    GOOGLE_CLOUD_BUCKET: str = "aivn"
    DATABASE_URL: str = "sqlite:///vn_story.db"
    GEMINI_API_KEY: str = None

    # Models
    STORY_MODEL: str = "gemini-2.5-flash"
    IMAGE_MODEL_MAIN: str = "gemini-3-pro-image-preview"
    IMAGE_MODEL: str = "gemini-3.1-flash-image-preview"
    POSE_MODEL: str = "gemini-3.1-flash-image-preview"
    POSE_FALLBACK_MODEL: str = "gemini-2.5-flash-image"
    AUDIO_MODEL: str = "gemini-2.5-pro-preview-tts"
    AUDIO_FALLBACK_MODEL: str = "gemini-2.5-flash-preview-tts"

    # Generation settings
    MAIN_CHAR_POSE_COUNT: str = "5"
    SIDE_CHAR_POSE_COUNT: str = "3"
    BACKGROUND_COUNT: int = 5

settings = Settings()

if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(settings.GOOGLE_APPLICATION_CREDENTIALS)
