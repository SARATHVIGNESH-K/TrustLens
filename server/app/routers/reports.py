"""
GET /api/report/{video_id}/pdf — generates (or regenerates) and streams back
the PDF verification report for a video.

Generated on-demand into settings.reports_dir rather than cached indefinitely,
so it always reflects the latest analysis if the video was re-analyzed.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app.models import VideoRecord
from app.config import settings
from app.services.pdf_report import generate_report_pdf
from app.services.storage import frames_dir_for
from app.services.ai_model import generate_heatmap, is_available as is_ai_model_available

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/report/{video_id}/pdf")
def download_report_pdf(video_id: str, db: Session = Depends(get_db)):
    video = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    output_path = settings.reports_dir / f"{video_id}.pdf"
    generate_report_pdf(video, video.analysis, output_path)

    safe_name = "".join(c for c in video.original_filename if c.isalnum() or c in " ._-") or "report"
    download_name = f"TrustLens_Report_{safe_name.rsplit('.', 1)[0]}.pdf"

    return FileResponse(
        path=str(output_path),
        media_type="application/pdf",
        filename=download_name,
    )

@router.get("/report/{video_id}/heatmap/{frame_filename}")
def get_frame_heatmap(video_id: str, frame_filename: str, db: Session = Depends(get_db)):
    """
    Generates or retrieves a heatmap explaining the deepfake model's decision for a specific frame.
    """
    video = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not is_ai_model_available():
        raise HTTPException(status_code=503, detail="AI Model is not loaded or available")

    # Validate frame_filename to avoid path traversal
    if "/" in frame_filename or "\\" in frame_filename or ".." in frame_filename:
        raise HTTPException(status_code=400, detail="Invalid frame filename")
    
    frames_dir = frames_dir_for(video_id)
    original_frame_path = frames_dir / frame_filename
    if not original_frame_path.exists():
        raise HTTPException(status_code=404, detail="Original frame not found")

    heatmap_filename = f"heatmap_{frame_filename}"
    heatmap_path = frames_dir / heatmap_filename

    # If the heatmap doesn't exist, generate it
    if not heatmap_path.exists():
        success = generate_heatmap(str(original_frame_path), str(heatmap_path))
        if not success:
            raise HTTPException(status_code=500, detail="Failed to generate heatmap")

    return FileResponse(
        path=str(heatmap_path),
        media_type="image/jpeg",
    )
