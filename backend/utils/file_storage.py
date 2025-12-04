"""
File storage utilities for S3/MinIO.
"""

import logging
from typing import Optional, BinaryIO
from datetime import timedelta
import os
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from minio import Minio
from minio.error import S3Error

from config import settings

logger = logging.getLogger(__name__)


class FileStorage:
    """Unified file storage interface for S3/MinIO."""

    def __init__(self):
        """Initialize file storage client."""
        self.use_minio = settings.USE_MINIO

        if self.use_minio and settings.MINIO_ENDPOINT:
            # Use MinIO
            logger.info("Initializing MinIO client")
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=False,  # Use HTTP for local development
            )
            self.bucket_name = settings.AWS_BUCKET_NAME

            # Create bucket if it doesn't exist
            try:
                if not self.client.bucket_exists(self.bucket_name):
                    self.client.make_bucket(self.bucket_name)
                    logger.info(f"Created MinIO bucket: {self.bucket_name}")
            except S3Error as e:
                logger.error(f"Error creating MinIO bucket: {e}")

        else:
            # Use AWS S3
            logger.info("Initializing AWS S3 client")
            self.client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            self.bucket_name = settings.AWS_BUCKET_NAME

    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        content_type: Optional[str] = None,
        folder: str = "",
    ) -> str:
        """
        Upload a file to storage.

        Args:
            file_data: File data as binary stream
            file_name: Name of the file
            content_type: MIME type of the file
            folder: Optional folder/prefix for organization

        Returns:
            Storage path of uploaded file
        """
        # Generate unique file name to avoid collisions
        unique_name = f"{uuid4()}_{file_name}"
        object_name = f"{folder}/{unique_name}" if folder else unique_name

        try:
            if self.use_minio:
                # Upload to MinIO
                file_data.seek(0, os.SEEK_END)
                file_size = file_data.tell()
                file_data.seek(0)

                self.client.put_object(
                    self.bucket_name,
                    object_name,
                    file_data,
                    file_size,
                    content_type=content_type,
                )
            else:
                # Upload to S3
                extra_args = {}
                if content_type:
                    extra_args["ContentType"] = content_type

                self.client.upload_fileobj(
                    file_data, self.bucket_name, object_name, ExtraArgs=extra_args
                )

            storage_path = f"s3://{self.bucket_name}/{object_name}"
            logger.info(f"File uploaded successfully: {storage_path}")

            return storage_path

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise

    def upload_file_from_path(
        self,
        local_path: str,
        object_name: Optional[str] = None,
        content_type: Optional[str] = None,
        folder: str = "",
    ) -> str:
        """
        Upload a file from local path.

        Args:
            local_path: Path to local file
            object_name: Optional custom object name
            content_type: MIME type of the file
            folder: Optional folder/prefix

        Returns:
            Storage path of uploaded file
        """
        if object_name is None:
            object_name = os.path.basename(local_path)

        unique_name = f"{uuid4()}_{object_name}"
        full_object_name = f"{folder}/{unique_name}" if folder else unique_name

        try:
            if self.use_minio:
                self.client.fput_object(
                    self.bucket_name,
                    full_object_name,
                    local_path,
                    content_type=content_type,
                )
            else:
                extra_args = {}
                if content_type:
                    extra_args["ContentType"] = content_type

                self.client.upload_file(
                    local_path, self.bucket_name, full_object_name, ExtraArgs=extra_args
                )

            storage_path = f"s3://{self.bucket_name}/{full_object_name}"
            logger.info(f"File uploaded from path: {storage_path}")

            return storage_path

        except Exception as e:
            logger.error(f"Error uploading file from path: {e}")
            raise

    def download_file(self, storage_path: str, local_path: str) -> None:
        """
        Download a file from storage to local path.

        Args:
            storage_path: Storage path (e.g., s3://bucket/object)
            local_path: Local path to save file
        """
        # Extract object name from storage path
        object_name = storage_path.replace(f"s3://{self.bucket_name}/", "")

        try:
            if self.use_minio:
                self.client.fget_object(self.bucket_name, object_name, local_path)
            else:
                self.client.download_file(self.bucket_name, object_name, local_path)

            logger.info(f"File downloaded: {storage_path} -> {local_path}")

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise

    def generate_presigned_url(
        self, storage_path: str, expiration: int = 3600
    ) -> str:
        """
        Generate a presigned URL for temporary file access.

        Args:
            storage_path: Storage path (e.g., s3://bucket/object)
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL
        """
        # Extract object name from storage path
        object_name = storage_path.replace(f"s3://{self.bucket_name}/", "")

        try:
            if self.use_minio:
                url = self.client.presigned_get_object(
                    self.bucket_name, object_name, expires=timedelta(seconds=expiration)
                )
            else:
                url = self.client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": object_name},
                    ExpiresIn=expiration,
                )

            logger.info(f"Generated presigned URL for: {storage_path}")

            return url

        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

    def delete_file(self, storage_path: str) -> None:
        """
        Delete a file from storage.

        Args:
            storage_path: Storage path (e.g., s3://bucket/object)
        """
        # Extract object name from storage path
        object_name = storage_path.replace(f"s3://{self.bucket_name}/", "")

        try:
            if self.use_minio:
                self.client.remove_object(self.bucket_name, object_name)
            else:
                self.client.delete_object(Bucket=self.bucket_name, Key=object_name)

            logger.info(f"File deleted: {storage_path}")

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise
