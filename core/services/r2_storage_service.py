"""Service for uploading and downloading files from Cloudflare R2."""

import io
from typing import Optional

import boto3
from botocore.config import Config
from loguru import logger

from shared.config import settings


class R2StorageService:
    def __init__(self):
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        self._bucket = settings.R2_BUCKET_NAME

    def upload_file(
        self,
        file_data: bytes,
        object_key: str,
        content_type: str = "audio/mpeg",
    ) -> str:
        """Upload file bytes to R2. Returns the object key."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=object_key,
            Body=file_data,
            ContentType=content_type,
        )
        logger.info("Uploaded to R2: bucket={} key={}", self._bucket, object_key)
        return object_key

    def download_file(self, object_key: str) -> bytes:
        """Download file from R2. Returns raw bytes."""
        response = self._client.get_object(
            Bucket=self._bucket,
            Key=object_key,
        )
        data = response["Body"].read()
        logger.info("Downloaded from R2: key={} size={}", object_key, len(data))
        return data

    def generate_presigned_url(
        self, object_key: str, expiration: int = 3600
    ) -> str:
        """Generate a presigned URL for downloading the file.

        Args:
            object_key: The R2 object key.
            expiration: URL expiry in seconds (default 1 hour).
        """
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": object_key},
            ExpiresIn=expiration,
        )
        return url

    def delete_file(self, object_key: str) -> None:
        """Delete a file from R2."""
        self._client.delete_object(
            Bucket=self._bucket,
            Key=object_key,
        )
        logger.info("Deleted from R2: key={}", object_key)
