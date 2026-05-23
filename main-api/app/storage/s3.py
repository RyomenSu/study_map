import asyncio
from functools import partial

import boto3
from fastapi import UploadFile

from app.config import settings

_client = None


def get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
    return _client


async def upload_file(file: UploadFile, key: str) -> str:
    client = get_client()
    contents = await file.read()
    fn = partial(
        client.put_object,
        Bucket=settings.s3_bucket,
        Key=key,
        Body=contents,
        ContentType=file.content_type or "application/octet-stream",
    )
    await asyncio.get_event_loop().run_in_executor(None, fn)
    return key
