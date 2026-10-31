"""File storage integration: a private storage provider + public links served by the API.

Storage is never public. Every public download passes through the API, which checks
revocation and expiry, so links never expose storage credentials or internal addresses.
Provider: STORAGE_BACKEND=s3 (MinIO / any S3-compatible) or local (server disk).
"""
from storage.backends import backend, ObjectMissing
from storage.files import ensure_bucket, put_file, open_object, download_to, delete_object
from storage.links import public_url, resolve_link, revoke_file, delete_file

__all__ = ["backend", "ObjectMissing", "ensure_bucket", "put_file", "open_object", "download_to", "delete_object",
           "public_url", "resolve_link", "revoke_file", "delete_file"]
