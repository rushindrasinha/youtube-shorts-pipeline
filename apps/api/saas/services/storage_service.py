"""S3-compatible storage for media files (Cloudflare R2, MinIO, AWS S3)."""

import boto3
from botocore.config import Config

from ..settings import settings


class StorageService:
    """S3-compatible storage for media files."""

    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.S3_BUCKET_NAME
        self.public_url = settings.S3_PUBLIC_URL

    def upload_file(
        self, local_path: str, s3_key: str, content_type: str = "application/octet-stream"
    ) -> dict:
        """Upload a file to S3. Returns dict with s3_key and public_url."""
        self.s3.upload_file(
            local_path,
            self.bucket,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )
        return {
            "s3_key": s3_key,
            "public_url": f"{self.public_url}/{s3_key}",
        }

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a presigned download URL (1 hour default)."""
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=expires_in,
        )

    def delete_file(self, s3_key: str):
        """Delete a file from S3."""
        self.s3.delete_object(Bucket=self.bucket, Key=s3_key)

    def delete_prefix(self, prefix: str):
        """Delete all files under a prefix (e.g., user_id/job_id/)."""
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                self.s3.delete_object(Bucket=self.bucket, Key=obj["Key"])
