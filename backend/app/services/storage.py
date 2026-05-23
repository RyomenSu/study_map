import uuid
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings


def _s3_client(public: bool = False):
    """
    public=False  → internal endpoint (rustfs:9000 inside Docker), used for all operations.
    public=True   → public endpoint (localhost:9000), used only for presigned URLs
                    so the browser can actually reach the link.
    """
    endpoint = settings.RUSTFS_PUBLIC_ENDPOINT if public else settings.RUSTFS_ENDPOINT
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.RUSTFS_ACCESS_KEY,
        aws_secret_access_key=settings.RUSTFS_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    client = _s3_client()
    try:
        client.head_bucket(Bucket=settings.RUSTFS_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=settings.RUSTFS_BUCKET)


def upload_file(file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
    client = _s3_client()
    key = f"submissions/{uuid.uuid4()}/{filename}"
    client.put_object(
        Bucket=settings.RUSTFS_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return key


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    # Use the public endpoint so the URL is browser-accessible
    client = _s3_client(public=True)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.RUSTFS_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )


def delete_file(key: str) -> None:
    client = _s3_client()
    client.delete_object(Bucket=settings.RUSTFS_BUCKET, Key=key)
