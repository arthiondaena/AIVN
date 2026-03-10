from google.cloud import storage
import os
import logging
from core.config import settings

logger = logging.getLogger(__name__)

def upload_blob(source_file_path: str, destination_blob_name: str) -> str:
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(settings.GOOGLE_CLOUD_BUCKET)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_path)

    logger.info(f"File {source_file_path} uploaded to {destination_blob_name}.")
    return f"gs://{settings.GOOGLE_CLOUD_BUCKET}/{destination_blob_name}"

def download_blob(source_blob_name: str, destination_file_path: str):
    """Downloads a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(settings.GOOGLE_CLOUD_BUCKET)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_path)

    logger.info(f"Blob {source_blob_name} downloaded to {destination_file_path}.")
