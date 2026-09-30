"""
Central configuration for TrustLens backend.
Reads from environment variables / .env file, with sane local defaults.
"""
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent  # /server


class Settings(BaseSettings):
    app_name: str = "TrustLens API"
    api_prefix: str = "/api"

    database_url: str = f"sqlite:///{BASE_DIR / 'trustlens.db'}"

    upload_dir: Path = BASE_DIR / "uploads"
    frames_dir: Path = BASE_DIR / "frames"
    reports_dir: Path = BASE_DIR / "reports"
    models_dir: Path = BASE_DIR / "models"

    max_upload_mb: int = 500
    allowed_extensions: tuple[str, ...] = (".mp4", ".avi", ".mov", ".mkv")

    # Frame extraction: one frame every N milliseconds
    frame_interval_ms: int = 500

    # Hugging Face API (optional, for real model inference)
    hf_api_token: str | None = None

    # JWT (used once auth is wired up)
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure runtime directories exist on import
for d in (settings.upload_dir, settings.frames_dir, settings.reports_dir, settings.models_dir):
    d.mkdir(parents=True, exist_ok=True)
