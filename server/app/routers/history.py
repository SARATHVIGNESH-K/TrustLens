"""
GET  /api/history           — list all analyzed videos, newest first
DELETE /api/history/{id}    — delete a video record + its files
GET  /api/report/{id}       — full detail for one video + its analysis
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import VideoRecord
from app.schemas import HistoryItem, VideoWithAnalysis, VideoMetadata as VideoMetadataSchema, AnalysisResponse
from app.services.storage import delete_video_artifacts

router = APIRouter(prefix="/api", tags=["history"])


def _format_date(dt) -> str:
    if not dt:
        return ""
    # Avoid %-d / %#d (platform-specific) — strip leading zero manually instead.
    day = str(dt.day)
    return dt.strftime(f"%b {day}, %Y")


def _format_duration(seconds: float | None) -> str:
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


@router.get("/history", response_model=list[HistoryItem])
def list_history(db: Session = Depends(get_db)):
    videos = db.query(VideoRecord).order_by(VideoRecord.uploaded_at.desc()).all()
    items = []
    for v in videos:
        fake_prob = v.analysis.fake_probability if v.analysis else None
        auth_score = round(100.0 - fake_prob, 1) if fake_prob is not None else None
        # Score is formatted as authenticity score when authentic, or manipulation risk when flagged
        display_score = auth_score if (v.analysis and v.analysis.verdict == "Authentic") else fake_prob

        items.append(
            HistoryItem(
                id=v.id,
                filename=v.original_filename,
                date=_format_date(v.uploaded_at),
                duration=_format_duration(v.duration_sec),
                verdict=v.analysis.verdict if v.analysis else None,
                score=display_score,
                fake_probability=fake_prob,
                authenticity_score=auth_score,
            )
        )
    return items


@router.delete("/history/{video_id}")
def delete_history_item(video_id: str, db: Session = Depends(get_db)):
    video = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    delete_video_artifacts(video_id, video.stored_path)
    db.delete(video)  # cascades to AnalysisResult via FK if configured; SQLite here is simple 1:1
    db.commit()
    return {"deleted": video_id}


@router.get("/report/{video_id}", response_model=VideoWithAnalysis)
def get_report(video_id: str, db: Session = Depends(get_db)):
    video = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    frame_urls = []
    if video.frames_dir:
        frames_path = Path(video.frames_dir)
        if frames_path.exists():
            frame_files = sorted(frames_path.glob("frame_*.jpg"))
            frame_urls = [f"/frames/{video_id}/{f.name}" for f in frame_files]

    video_url = None
    if video.stored_path and Path(video.stored_path).exists():
        video_url = f"/media/{Path(video.stored_path).name}"

    return VideoWithAnalysis(
        id=video.id,
        original_filename=video.original_filename,
        status=video.status,
        uploaded_at=video.uploaded_at,
        size_bytes=video.size_bytes,
        metadata=VideoMetadataSchema(
            duration_sec=video.duration_sec,
            fps=video.fps,
            width=video.width,
            height=video.height,
            codec=video.codec,
            bitrate=video.bitrate,
            frame_count=video.frame_count,
            creation_time=video.creation_time,
        ),
        video_url=video_url,
        frame_urls=frame_urls,
        analysis=AnalysisResponse.model_validate(video.analysis) if video.analysis else None,
    )
