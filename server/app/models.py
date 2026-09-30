"""
ORM models.

VideoRecord      — one row per uploaded video, plus extracted metadata.
AnalysisResult   — one row per completed analysis (score, verdict, reasons, timeline).
User             — minimal user table, ready for the auth module.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Integer, default=0)  # 0/1 flag, kept simple for SQLite
    created_at = Column(DateTime, default=datetime.utcnow)

    videos = relationship("VideoRecord", back_populates="owner")


class VideoRecord(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=gen_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)

    original_filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=False)

    # Metadata extracted via ffprobe
    duration_sec = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    codec = Column(String, nullable=True)
    bitrate = Column(Integer, nullable=True)
    frame_count = Column(Integer, nullable=True)
    creation_time = Column(String, nullable=True)

    frames_dir = Column(String, nullable=True)
    extracted_frame_count = Column(Integer, nullable=True)

    status = Column(String, default="uploaded")  # uploaded -> processing -> analyzed -> failed
    error_message = Column(Text, nullable=True)

    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="videos")
    analysis = relationship("AnalysisResult", back_populates="video", uselist=False)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True, default=gen_uuid)
    video_id = Column(String, ForeignKey("videos.id"), unique=True, nullable=False)

    verdict = Column(String, nullable=True)  # "Authentic" | "Deepfake" | "Face Swap" | "AI Generated"
    fake_probability = Column(Float, nullable=True)  # 0-100
    confidence_label = Column(String, nullable=True)  # e.g. "Very High"
    risk_level = Column(String, nullable=True)  # "Low" | "Medium" | "High"

    reasons = Column(JSON, nullable=True)  # list[str]
    timeline_segments = Column(JSON, nullable=True)  # list[{start,end,status,reason}]
    forensic_signals = Column(JSON, nullable=True)  # raw signal dump for the report

    model_used = Column(String, nullable=True)  # "forensics-heuristic-v1" | model checkpoint name
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("VideoRecord", back_populates="analysis")
