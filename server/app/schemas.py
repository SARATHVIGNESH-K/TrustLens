"""
Pydantic schemas — the API's public request/response contracts.
Kept separate from ORM models (app/models.py) so internal DB shape can change
without breaking the API, and vice versa.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, computed_field

# Note: `protected_namespaces=()` below disables Pydantic's "model_" prefix
# warning — we use `model_used` as a legitimate field name (which AI model
# produced this analysis), not a Pydantic internal.


class VideoMetadata(BaseModel):
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None
    frame_count: Optional[int] = None
    creation_time: Optional[str] = None


class VideoUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    size_bytes: int
    status: str
    metadata: Optional[VideoMetadata] = None
    extracted_frame_count: Optional[int] = None
    uploaded_at: datetime


class TimelineSegment(BaseModel):
    start: int
    end: int
    status: str  # "normal" | "suspicious"
    reason: str


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    video_id: str
    verdict: Optional[str] = None
    fake_probability: Optional[float] = None
    confidence_label: Optional[str] = None
    risk_level: Optional[str] = None
    reasons: list[str] = []
    timeline_segments: list[TimelineSegment] = []
    forensic_signals: dict = {}
    model_used: Optional[str] = None
    analyzed_at: datetime

    @computed_field
    def authenticity_score(self) -> Optional[float]:
        if self.fake_probability is not None:
            return round(max(0.0, min(100.0, 100.0 - self.fake_probability)), 1)
        return None


class VideoWithAnalysis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    status: str
    uploaded_at: datetime
    metadata: Optional[VideoMetadata] = None
    size_bytes: Optional[int] = None
    video_url: Optional[str] = None
    frame_urls: list[str] = []
    analysis: Optional[AnalysisResponse] = None


class HistoryItem(BaseModel):
    id: str
    filename: str
    date: str
    duration: str
    verdict: Optional[str] = None
    score: Optional[float] = None
    fake_probability: Optional[float] = None
    authenticity_score: Optional[float] = None


class StatsResponse(BaseModel):
    total_analyzed: int
    flagged_fake: int
    confirmed_authentic: int
    avg_confidence: float
