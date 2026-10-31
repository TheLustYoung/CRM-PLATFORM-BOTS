"""Storage providers. The rest of the platform only sees this small interface, so the provider
is switched with STORAGE_BACKEND (s3 | local) without touching bots, workers or the API."""
import shutil
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from backend.config import settings


class ObjectMissing(Exception):
    """The database references an object that the storage no longer has."""


class S3Backend:
    """Any S3-compatible service: bundled MinIO, AWS S3, Backblaze B2, Cloudflare R2, ..."""

    def __init__(self):
        s = settings()
        self.bucket = s.s3_bucket
        self.client = boto3.client("s3", endpoint_url=s.s3_endpoint, aws_access_key_id=s.s3_access_key,
                                   aws_secret_access_key=s.s3_secret_key.get_secret_value(), region_name=s.s3_region)

    def ensure(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code")) not in {"404", "NoSuchBucket"}:
                raise
            self.client.create_bucket(Bucket=self.bucket)

    def ping(self):
        self.client.head_bucket(Bucket=self.bucket)

    def upload(self, path: Path, key: str, mime: str) -> int:
        self.client.upload_file(str(path), self.bucket, key, ExtraArgs={"ContentType": mime})
        return self.client.head_object(Bucket=self.bucket, Key=key)["ContentLength"]

    def open(self, key: str):
        try:
            body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"]
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code")) in {"404", "NoSuchKey"}:
                raise ObjectMissing(key) from None
            raise
        return body.iter_chunks(chunk_size=1024 * 1024), body.close

    def download_to(self, key: str, destination: Path):
        try:
            self.client.download_file(self.bucket, key, str(destination))
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code")) in {"404", "NoSuchKey"}:
                raise ObjectMissing(key) from None
            raise

    def delete(self, key: str):
        self.client.delete_object(Bucket=self.bucket, Key=key)


class LocalBackend:
    """Files on the server disk (STORAGE_DIR). Simple single-server setups and local development."""

    def __init__(self):
        self.root = Path(settings().storage_dir).resolve()

    def path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("invalid object key")
        return target

    def ensure(self):
        self.root.mkdir(parents=True, exist_ok=True)

    def ping(self):
        if not self.root.is_dir():
            raise FileNotFoundError(self.root)

    def upload(self, path: Path, key: str, mime: str) -> int:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        return target.stat().st_size

    def open(self, key: str):
        target = self.path(key)
        if not target.is_file():
            raise ObjectMissing(key)
        handle = target.open("rb")
        return iter(lambda: handle.read(1024 * 1024), b""), handle.close

    def download_to(self, key: str, destination: Path):
        target = self.path(key)
        if not target.is_file():
            raise ObjectMissing(key)
        shutil.copyfile(target, destination)

    def delete(self, key: str):
        self.path(key).unlink(missing_ok=True)


def backend() -> S3Backend | LocalBackend:
    # Created per call (as cheap as a boto3 client); keeps credentials and test mocks current.
    return LocalBackend() if settings().storage_backend == "local" else S3Backend()
