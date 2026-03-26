import boto3
from botocore.config import Config

from shared.config import settings


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def generate_presigned_url(object_key: str, expires_in: int = 3600) -> str:
    client = get_r2_client()
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.R2_BUCKET_NAME,
            "Key": object_key,
        },
        ExpiresIn=expires_in,
    )
