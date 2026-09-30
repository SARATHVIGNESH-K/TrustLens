"""
GET /api/stats — aggregate numbers for the dashboard stat cards.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import AnalysisResult
from app.schemas import StatsResponse

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(AnalysisResult.id)).scalar() or 0
    flagged = (
        db.query(func.count(AnalysisResult.id))
        .filter(AnalysisResult.verdict != "Authentic")
        .scalar()
        or 0
    )
    authentic = total - flagged
    avg_conf = db.query(func.avg(AnalysisResult.fake_probability)).scalar() or 0.0

    return StatsResponse(
        total_analyzed=total,
        flagged_fake=flagged,
        confirmed_authentic=authentic,
        avg_confidence=round(float(avg_conf), 1),
    )
