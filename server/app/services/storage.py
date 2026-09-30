"""
File storage helpers — saving uploads, validating extension/size, generating
per-video working directories under frames_dir.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


class UploadValidationError(Exception):
    pass


def validate_upload(file: UploadFile, size_bytes: int) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_extensions:
        raise UploadValidationError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(settings.allowed_extensions)}"
        )
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise UploadValidationError(f"File exceeds {settings.max_upload_mb}MB limit")


def save_upload(file: UploadFile, video_id: str) -> tuple[Path, int]:
    """Streams the upload to disk in chunks (avoids loading huge files into memory).
    Returns (saved_path, size_bytes)."""
    ext = Path(file.filename or "").suffix.lower()
    dest = settings.upload_dir / f"{video_id}{ext}"

    size = 0
    with open(dest, "wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            out.write(chunk)

    return dest, size


def frames_dir_for(video_id: str) -> Path:
    d = settings.frames_dir / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def delete_video_artifacts(video_id: str, stored_path: str | None) -> None:
    """Best-effort cleanup of a video's file and extracted frames."""
    if stored_path:
        p = Path(stored_path)
        if p.exists():
            p.unlink(missing_ok=True)
    frames_path = settings.frames_dir / video_id
    if frames_path.exists():
        shutil.rmtree(frames_path, ignore_errors=True)
