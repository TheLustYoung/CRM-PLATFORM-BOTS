import os
import secrets

# Test-only configuration; never point tests at a production database or bucket.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("JWT_SECRET", secrets.token_urlsafe(48))
for bot in ("VIDEO", "MEDIA", "FILES"):
    os.environ.setdefault(bot + "_SERVICE_KEY", secrets.token_urlsafe(32))
    os.environ.setdefault(bot + "_BOT_TOKEN", "123:test-token")
os.environ.setdefault("S3_ACCESS_KEY", "test-access")
os.environ.setdefault("S3_SECRET_KEY", secrets.token_urlsafe(32))
os.environ["S3_ENDPOINT"] = "https://s3.amazonaws.com"
os.environ["ADMIN_ORIGIN"] = "http://testserver"
os.environ["COOKIE_SECURE"] = "false"
os.environ["EGRESS_PROXY"] = ""
os.environ["AWS_EC2_METADATA_DISABLED"] = "true"
