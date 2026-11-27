import io
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.core import config

logger = logging.getLogger("campuscare.s3")

# Local fallback directory when AWS S3 credentials are not configured
_FALLBACK_DIR = Path(__file__).resolve().parents[2] / "storage" / "s3_local"
_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)


class S3StorageService:
    """
    AWS S3 Cloud Storage Service for PulseCare.
    Provides scalable object storage for:
      - Digital Prescription PDFs & Clinical Summaries
      - Patient Medical Records, Diagnostic Reports & Lab Attachments
      - Automated Database Backup Snapshots
    Includes automatic fallback to local persistent disk storage when S3 credentials are unset.
    """

    def __init__(self):
        self.region = config.AWS_REGION or "ap-southeast-2"
        self.bucket = config.AWS_S3_BUCKET_NAME or "pulsecare-medical-records"
        self.endpoint_url = config.AWS_S3_ENDPOINT_URL
        self._s3_client = None
        self._is_cloud_s3 = False

        self._initialize_client()

    def _initialize_client(self):
        """Attempts to initialize boto3 S3 client if credentials or IAM roles exist."""
        try:
            import boto3
            from botocore.config import Config

            client_kwargs = {
                "region_name": self.region,
                "config": Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
            }
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url

            if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
                client_kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
                client_kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY

            self._s3_client = boto3.client("s3", **client_kwargs)
            # Lightweight probe to check if bucket is reachable
            if config.AWS_ACCESS_KEY_ID:
                try:
                    self._s3_client.head_bucket(Bucket=self.bucket)
                    self._is_cloud_s3 = True
                    logger.info("Connected to AWS S3 bucket: %s (region: %s)", self.bucket, self.region)
                except Exception as b_err:
                    logger.warning("AWS S3 bucket '%s' check returned: %s. S3 client ready.", self.bucket, b_err)
                    self._is_cloud_s3 = True
            else:
                self._is_cloud_s3 = False
                logger.info("AWS S3 credentials not provided. Using local persistent storage adapter.")
        except Exception as exc:
            self._s3_client = None
            self._is_cloud_s3 = False
            logger.warning("Boto3 S3 initialization notice: %s. Using local fallback.", exc)

    @property
    def is_cloud(self) -> bool:
        return self._is_cloud_s3 and self._s3_client is not None

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "documents",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Uploads a binary object to AWS S3 (or local fallback).
        Returns a descriptor containing s3_key, bucket, provider, size, and URL.
        """
        sanitized_filename = os.path.basename(filename).replace(" ", "_")
        s3_key = f"{folder}/{uuid.uuid4().hex[:8]}_{sanitized_filename}"

        if self.is_cloud:
            try:
                extra_args = {"ContentType": content_type}
                if metadata:
                    extra_args["Metadata"] = metadata

                self._s3_client.upload_fileobj(
                    io.BytesIO(file_bytes),
                    self.bucket,
                    s3_key,
                    ExtraArgs=extra_args,
                )
                url = self.generate_presigned_url(s3_key, expires_in=86400)
                logger.info("Successfully uploaded object to AWS S3: s3://%s/%s", self.bucket, s3_key)
                return {
                    "provider": "AWS_S3",
                    "bucket": self.bucket,
                    "s3_key": s3_key,
                    "filename": sanitized_filename,
                    "size_bytes": len(file_bytes),
                    "content_type": content_type,
                    "url": url,
                    "uploaded_at": datetime.utcnow().isoformat() + "Z",
                }
            except Exception as exc:
                logger.error("Failed to upload to AWS S3, falling back to local disk: %s", exc)

        # Local storage fallback
        dest_path = _FALLBACK_DIR / folder / f"{uuid.uuid4().hex[:8]}_{sanitized_filename}"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(file_bytes)

        return {
            "provider": "LOCAL_STORAGE_FALLBACK",
            "bucket": "local-disk",
            "s3_key": f"{folder}/{dest_path.name}",
            "filename": sanitized_filename,
            "size_bytes": len(file_bytes),
            "content_type": content_type,
            "url": f"/api/cloud/documents/download?key={folder}/{dest_path.name}",
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
        }

    def generate_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """
        Generates a secure temporary pre-signed URL for direct browser access.
        """
        if self.is_cloud:
            try:
                return self._s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": s3_key},
                    ExpiresIn=expires_in,
                )
            except Exception as exc:
                logger.warning("Could not generate S3 pre-signed URL: %s", exc)

        return f"/api/cloud/documents/download?key={s3_key}"

    def backup_database_to_s3(self, db_path: str) -> Dict[str, Any]:
        """
        Takes a snapshot of the active database file and pushes it to S3 under backups/.
        """
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found at {db_path}")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"campuscare_backup_{timestamp}.db"
        content = Path(db_path).read_bytes()

        return self.upload_file(
            file_bytes=content,
            filename=filename,
            content_type="application/x-sqlite3",
            folder="database_backups",
            metadata={"source": "PulseCare_Automated_Snapshot", "timestamp": timestamp},
        )

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns the active health and status of the AWS S3 storage layer."""
        return {
            "service": "AWS S3 (Simple Storage Service)",
            "active_provider": "AWS_S3" if self.is_cloud else "LOCAL_STORAGE_FALLBACK",
            "bucket_name": self.bucket,
            "region": self.region,
            "cloud_connected": self.is_cloud,
            "local_storage_path": str(_FALLBACK_DIR),
            "signature_version": "v4",
        }


# Singleton instance for application-wide reuse
s3_storage = S3StorageService()
