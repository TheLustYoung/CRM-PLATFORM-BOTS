from functools import lru_cache
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BOT_KINDS = ("video", "media", "files")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: SecretStr = Field(min_length=32)
    admin_origin: str = "http://localhost:8080"
    cookie_secure: bool = True
    public_files_url: str = "https://files.example.com"
    api_internal_url: str = "http://api:8000"
    video_bot_token: SecretStr = SecretStr("")
    media_bot_token: SecretStr = SecretStr("")
    files_bot_token: SecretStr = SecretStr("")
    video_service_key: SecretStr = Field(min_length=32)
    media_service_key: SecretStr = Field(min_length=32)
    files_service_key: SecretStr = Field(min_length=32)
    storage_backend: str = Field(default="s3", pattern="^(s3|local)$")
    storage_dir: str = "/data/files"
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str
    s3_secret_key: SecretStr
    s3_bucket: str = "media"
    s3_region: str = "us-east-1"
    egress_proxy: str = "http://egress:3128"  # SSRF guard for outgoing worker requests (infrastructure/egress.py)
    sentry_dsn: SecretStr = SecretStr("")  # optional error tracking (Sentry or GlitchTip), see backend/observability.py
    environment: str = "production"  # shown in error reports
    default_language: str = "en"
    telegram_send_bytes: int = 49_000_000
    telegram_receive_bytes: int = 19_000_000
    max_download_bytes: int = 2_000_000_000
    max_upload_bytes: int = 19_000_000
    retention_days: int = 7
    daily_jobs: int = 20
    job_timeout: int = 900
    min_free_disk_bytes: int = 300_000_000
    temp_root: str = "/data/files/.work"  # on disk: long videos do not fit the RAM-backed /tmp

    @model_validator(mode="after")
    def reject_example_secrets(self):
        values = [self.jwt_secret, self.s3_secret_key, self.video_service_key, self.media_service_key, self.files_service_key]
        if any("CHANGE_ME" in value.get_secret_value() for value in values) or "CHANGE_ME" in self.database_url:
            raise ValueError("Replace all example secrets before starting the application")
        return self

    def bot_token(self, kind: str) -> str:
        """The token set in the dashboard (Bots page), else the one in .env."""
        from backend.services.bot_tokens import override
        return override(kind) or self.env_bot_token(kind)

    def env_bot_token(self, kind: str) -> str:
        return getattr(self, f"{kind}_bot_token").get_secret_value()

    def service_key(self, kind: str) -> str:
        return getattr(self, f"{kind}_service_key").get_secret_value()


@lru_cache
def settings() -> Settings:
    return Settings()
