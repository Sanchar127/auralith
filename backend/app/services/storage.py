from pathlib import Path

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.logger import logger


class StorageService:

    def __init__(self) -> None:

        self.bucket = settings.MINIO_BUCKET

        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        logger.info(
            "Initialized MinIO client (endpoint=%s, bucket=%s)",
            settings.MINIO_ENDPOINT,
            self.bucket,
        )

        self._ensure_bucket()

    def _ensure_bucket(self) -> None:

        try:

            if not self.client.bucket_exists(self.bucket):

                self.client.make_bucket(self.bucket)

                logger.info(
                    "Created MinIO bucket '%s'",
                    self.bucket,
                )

            else:

                logger.info(
                    "Using existing MinIO bucket '%s'",
                    self.bucket,
                )

        except Exception:

            logger.exception(
                "Failed to initialize MinIO bucket '%s'",
                self.bucket,
            )

            raise

    def upload_file(
        self,
        file_path: str,
        object_name: str | None = None,
        content_type: str | None = None,
    ) -> str:

        path = Path(file_path)

        if not path.exists():

            logger.error(
                "Upload failed. File does not exist: %s",
                path,
            )

            raise FileNotFoundError(path)

        if object_name is None:
            object_name = path.name

        if content_type is None:

            match path.suffix.lower():

                case ".mp3":
                    content_type = "audio/mpeg"

                case ".mid":
                    content_type = "audio/midi"

                case ".wav":
                    content_type = "audio/wav"

                case ".json":
                    content_type = "application/json"

                case _:
                    content_type = "application/octet-stream"

        logger.info(
            "Uploading '%s' -> '%s/%s'",
            path,
            self.bucket,
            object_name,
        )

        try:

            self.client.fput_object(
                bucket_name=self.bucket,
                object_name=object_name,
                file_path=str(path),
                content_type=content_type,
            )

            logger.info(
                "Successfully uploaded '%s'",
                object_name,
            )

            return object_name

        except Exception:

            logger.exception(
                "Failed to upload '%s'",
                object_name,
            )

            raise

    def download_file(
        self,
        object_name: str,
        destination: str,
    ) -> str:

        logger.info(
            "Downloading '%s' -> '%s'",
            object_name,
            destination,
        )

        try:

            self.client.fget_object(
                bucket_name=self.bucket,
                object_name=object_name,
                file_path=destination,
            )

            logger.info(
                "Successfully downloaded '%s'",
                object_name,
            )

            return destination

        except Exception:

            logger.exception(
                "Failed to download '%s'",
                object_name,
            )

            raise

    def delete_file(
        self,
        object_name: str,
    ) -> None:

        logger.info(
            "Deleting '%s'",
            object_name,
        )

        try:

            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=object_name,
            )

            logger.info(
                "Deleted '%s'",
                object_name,
            )

        except Exception:

            logger.exception(
                "Failed to delete '%s'",
                object_name,
            )

            raise

    def file_exists(
        self,
        object_name: str,
    ) -> bool:

        try:

            self.client.stat_object(
                self.bucket,
                object_name,
            )

            logger.debug(
                "Object exists: %s",
                object_name,
            )

            return True

        except S3Error:

            logger.debug(
                "Object not found: %s",
                object_name,
            )

            return False

        except Exception:

            logger.exception(
                "Failed checking object '%s'",
                object_name,
            )

            raise


storage_service = StorageService()