import os
from google.oauth2 import service_account
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='allow')
    GOOGLE_APPLICATION_CREDENTIALS: str = None
    GOOGLE_CLOUD_BUCKET: str = "visualnovel"
    DATABASE_URL: str = None
    VERTEX_API_KEY: str = None
    REMOVEBG_API_KEY: str = None

    # Models
    STORY_MODEL: str = "gemini-3-flash-preview"
    IMAGE_MODEL: str = "gemini-3-pro-image-preview"
    AUDIO_MODEL: str = "gemini-2.5-pro-preview-tts"
    # EMBEDDING_MODEL: str = "multimodalembedding@001"
    EMBEDDING_MODEL: str = "gemini-embedding-001"

settings = Settings()

if __name__ == "__main__":
    print(settings.GOOGLE_APPLICATION_CREDENTIALS)