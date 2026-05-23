import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),        # для MinIO
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )

def download_pdf_from_s3(s3_path: str) -> bytes:
    """
    s3_path формат: bucket-name/path/to/file.pdf
    """
    client = get_s3_client()
    parts = s3_path.split("/", 1)
    bucket = parts[0]
    key = parts[1]

    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()