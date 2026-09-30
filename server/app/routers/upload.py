"""
POST /api/upload

Accepts a video file, validates it, saves it to disk, extracts metadata via
ffprobe, and creates the VideoRecord row. Does NOT run analysis — that's a
separate step (POST /api/analyze/{video_id}) so the UI can show "uploaded"
before committing to the (slower) analysis pass.
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import VideoRecord
from app.schemas import VideoUploadResponse, VideoMetadata as VideoMetadataSchema
from app.services.storage import validate_upload, save_upload, UploadValidationError
from app.services.video_processor import extract_metadata, VideoProcessingError
from app.models import gen_uuid

logger = logging.getLogger("trustlens.upload")

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    video_id = gen_uuid()

    # Peek size without fully loading into memory: read once while saving.
    try:
        validate_upload(file, size_bytes=0)  # extension check up front
        saved_path, size_bytes = save_upload(file, video_id)
        validate_upload(file, size_bytes=size_bytes)  # size check after write
    except UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    record = VideoRecord(
        id=video_id,
        original_filename=file.filename,
        stored_path=str(saved_path),
        content_type=file.content_type,
        size_bytes=size_bytes,
        status="uploaded",
    )

    try:
        meta = extract_metadata(saved_path)
        record.duration_sec = meta.duration_sec
        record.fps = meta.fps
        record.width = meta.width
        record.height = meta.height
        record.codec = meta.codec
        record.bitrate = meta.bitrate
        record.frame_count = meta.frame_count
        record.creation_time = meta.creation_time
    except VideoProcessingError as e:
        logger.warning("Metadata extraction failed for %s: %s", video_id, e)
        record.status = "uploaded"
        record.error_message = f"metadata extraction failed: {e}"

    db.add(record)
    db.commit()
    db.refresh(record)

    return VideoUploadResponse(
        id=record.id,
        original_filename=record.original_filename,
        size_bytes=record.size_bytes,
        status=record.status,
        metadata=VideoMetadataSchema(
            duration_sec=record.duration_sec,
            fps=record.fps,
            width=record.width,
            height=record.height,
            codec=record.codec,
            bitrate=record.bitrate,
            frame_count=record.frame_count,
            creation_time=record.creation_time,
        ),
        extracted_frame_count=record.extracted_frame_count,
        uploaded_at=record.uploaded_at,
    )
