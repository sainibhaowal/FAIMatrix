"""
FAIM S3/MinIO Storage Client

Provides S3-compatible blob storage for documents and attachments.
Works with MinIO (self-hosted) or AWS S3.
"""
import os
import logging
from typing import Optional, BinaryIO
from io import BytesIO

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

# Configuration from environment
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "faim-documents")
S3_REGION = os.getenv("S3_REGION", "us-east-1")


def get_s3_client():
    """Get configured S3 client (works with MinIO)."""
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
    )


def ensure_bucket_exists(bucket_name: str = None) -> bool:
    """Create bucket if it doesn't exist."""
    bucket = bucket_name or S3_BUCKET_NAME
    client = get_s3_client()
    
    try:
        client.head_bucket(Bucket=bucket)
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            try:
                client.create_bucket(Bucket=bucket)
                logger.info(f"Created S3 bucket: {bucket}")
                return True
            except ClientError as create_err:
                logger.error(f"Failed to create bucket: {create_err}")
                return False
        else:
            logger.error(f"Bucket check failed: {e}")
            return False
    except NoCredentialsError:
        logger.error("S3 credentials not configured")
        return False


def upload_file(
    file_obj: BinaryIO,
    key: str,
    bucket: str = None,
    content_type: str = "application/octet-stream",
    metadata: dict = None,
) -> str:
    """
    Upload a file to S3/MinIO.
    
    Args:
        file_obj: File-like object to upload
        key: S3 object key (path)
        bucket: Bucket name (defaults to S3_BUCKET_NAME)
        content_type: MIME type
        metadata: Optional metadata dict
    
    Returns:
        The S3 key on success
    
    Raises:
        Exception on failure
    """
    bucket = bucket or S3_BUCKET_NAME
    client = get_s3_client()
    
    # Ensure bucket exists
    ensure_bucket_exists(bucket)
    
    extra_args = {"ContentType": content_type}
    if metadata:
        extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}
    
    try:
        # Reset file position if possible
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        
        client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)
        logger.info(f"Uploaded to S3: {bucket}/{key}")
        return key
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        raise


def upload_bytes(
    data: bytes,
    key: str,
    bucket: str = None,
    content_type: str = "application/octet-stream",
    metadata: dict = None,
) -> str:
    """Upload bytes directly to S3."""
    return upload_file(BytesIO(data), key, bucket, content_type, metadata)


def download_file(key: str, bucket: str = None) -> bytes:
    """
    Download a file from S3/MinIO.
    
    Returns:
        File contents as bytes
    
    Raises:
        Exception if file not found or download fails
    """
    bucket = bucket or S3_BUCKET_NAME
    client = get_s3_client()
    
    try:
        response = client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "NoSuchKey":
            raise FileNotFoundError(f"S3 object not found: {bucket}/{key}")
        logger.error(f"S3 download failed: {e}")
        raise


def delete_file(key: str, bucket: str = None) -> bool:
    """
    Delete a file from S3/MinIO.
    
    Returns:
        True on success, False on failure
    """
    bucket = bucket or S3_BUCKET_NAME
    client = get_s3_client()
    
    try:
        client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted from S3: {bucket}/{key}")
        return True
    except ClientError as e:
        logger.error(f"S3 delete failed: {e}")
        return False


def get_presigned_url(
    key: str,
    bucket: str = None,
    expires_in: int = 3600,
    method: str = "get_object",
) -> str:
    """
    Generate a presigned URL for temporary access.
    
    Args:
        key: S3 object key
        bucket: Bucket name
        expires_in: Seconds until URL expires (default 1 hour)
        method: 'get_object' for download, 'put_object' for upload
    
    Returns:
        Presigned URL string
    """
    bucket = bucket or S3_BUCKET_NAME
    client = get_s3_client()
    
    try:
        url = client.generate_presigned_url(
            method,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise


def file_exists(key: str, bucket: str = None) -> bool:
    """Check if a file exists in S3."""
    bucket = bucket or S3_BUCKET_NAME
    client = get_s3_client()
    
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def get_file_info(key: str, bucket: str = None) -> Optional[dict]:
    """Get metadata about a file."""
    bucket = bucket or S3_BUCKET_NAME
    client = get_s3_client()
    
    try:
        response = client.head_object(Bucket=bucket, Key=key)
        return {
            "size": response.get("ContentLength", 0),
            "content_type": response.get("ContentType"),
            "last_modified": response.get("LastModified"),
            "metadata": response.get("Metadata", {}),
        }
    except ClientError:
        return None
