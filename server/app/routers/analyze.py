"""
POST /api/analyze/{video_id}

Runs the analysis pipeline on an already-uploaded video:
  1. Extract frames (OpenCV)
  2. Run ViT-based deepfake AI classifier (primary — high accuracy)
  3. Run classical forensic signal analysis (secondary — explainability)
  4. Blend scores and persist an AnalysisResult row

The AI model (ViT fine-tuned on deepfake datasets) is the primary detector.
The classical forensic signals supplement it with interpretable evidence even
when the AI model is unavailable.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import VideoRecord, AnalysisResult, gen_uuid
from app.schemas import AnalysisResponse
from app.config import settings
from app.services.video_processor import (
    extract_frames,
    extract_frames_array,
    extract_audio_wav,
    VideoProcessingError,
)
from app.services.forensics import run_forensic_analysis, combine_with_face_signals, overlay_ai_on_timeline
from app.services.face_signals import analyze_blinking, analyze_face_region_motion, analyze_lip_sync
from app.services.storage import frames_dir_for
from app.services import ai_model

logger = logging.getLogger("trustlens.analyze")

router = APIRouter(prefix="/api", tags=["analyze"])


def _blend_scores(ai_prob: float | None, heuristic_prob: float) -> tuple[float, str]:
    """
    Blends the AI model score (70% weight) with the forensic heuristic score
    (30% weight) when the AI model is available.  Falls back to heuristic-only
    when the model is unavailable.
    Returns (blended_fake_probability, model_name_string).
    """
    if ai_prob is not None:
        blended = ai_prob * 0.70 + heuristic_prob * 0.30
        return round(blended, 1), "vit-deepfake-v2 + forensics-heuristic-v1"
    return round(heuristic_prob, 1), "forensics-heuristic-v1"


def _build_ai_reasons(ai_result: dict, ai_prob: float) -> list[str]:
    """Generates human-readable AI-specific findings from the model output."""
    reasons = []
    if not ai_result.get("available"):
        return reasons
    high_risk = ai_result.get("high_risk_frame_count", 0)
    total = ai_result.get("total_frames_analyzed", 0)
    max_score = ai_result.get("max_frame_score", 0)

    if ai_prob >= 70:
        reasons.append(
            f"Deep-learning classifier (ViT) flagged {high_risk}/{total} frames "
            f"as AI-generated or manipulated (highest frame score: {max_score:.0%}, "
            f"mean: {ai_prob:.0f}%) — strong evidence of synthetic content"
        )
    elif ai_prob >= 45:
        reasons.append(
            f"Deep-learning classifier (ViT) shows elevated synthetic content "
            f"probability ({ai_prob:.0f}% avg, {high_risk}/{total} high-risk frames) "
            "— moderate evidence of AI generation or manipulation"
        )
    return reasons


def _verdict_from_probability(p: float) -> tuple[str, str]:
    """Maps a fake-probability score to a display verdict + risk level."""
    if p < 25:
        return "Authentic", "Low"
    if p < 45:
        return "Authentic", "Medium"
    if p < 65:
        return "Deepfake", "Medium"
    return "Deepfake", "High"


def _confidence_label(p: float) -> str:
    distance_from_mid = abs(p - 50)
    if distance_from_mid > 40:
        return "Very High"
    if distance_from_mid > 25:
        return "High"
    if distance_from_mid > 10:
        return "Moderate"
    return "Low"


@router.post("/analyze/{video_id}", response_model=AnalysisResponse)
def analyze_video(video_id: str, db: Session = Depends(get_db)):
    video = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    video.status = "processing"
    db.commit()

    try:
        out_dir = frames_dir_for(video_id)
        frame_paths = extract_frames(
            video.stored_path, out_dir, interval_ms=settings.frame_interval_ms
        )
        video.frames_dir = str(out_dir)
        video.extracted_frame_count = len(frame_paths)

        # ── Stage 1: ViT AI classifier (primary, high-accuracy detector) ──
        ai_result = ai_model.analyze_video_frames(frame_paths, max_frames=128)
        ai_prob = ai_result.get("fake_probability") if ai_result.get("available") else None
        if ai_prob is not None:
            logger.info("AI model score for %s: %.1f%%", video_id, ai_prob)
        else:
            logger.info("AI model unavailable for %s, reason: %s", video_id, ai_result.get("reason"))

        # ── Stage 2: Classical forensic heuristics (supplementary explainability) ──
        base_result = run_forensic_analysis(frame_paths, interval_ms=settings.frame_interval_ms)

        # Face-specific signals at dense sampling (blinks ~100–400ms window)
        dense_interval_ms = 100
        dense_frames = extract_frames_array(video.stored_path, interval_ms=dense_interval_ms)

        blink_result = analyze_blinking(dense_frames, interval_ms=dense_interval_ms)
        face_flow_result = analyze_face_region_motion(dense_frames)

        audio_wav_path = extract_audio_wav(
            video.stored_path, out_dir / "audio_tmp.wav"
        )
        lip_sync_result = analyze_lip_sync(
            dense_frames, wav_path=audio_wav_path, interval_ms=dense_interval_ms
        )
        if audio_wav_path and audio_wav_path.exists():
            audio_wav_path.unlink(missing_ok=True)

        forensic_result = combine_with_face_signals(
            base_result, blink_result, face_flow_result, lip_sync_result
        )

        # ── Stage 3: Blend AI + forensic scores ──
        final_fake_prob, model_used = _blend_scores(ai_prob, forensic_result["fake_probability"])

        # Merge reasons: AI findings first (most important), then forensic evidence
        ai_reasons = _build_ai_reasons(ai_result, ai_prob or 0.0)
        # Filter out the generic "no anomalies" message when AI found something
        forensic_reasons = [
            r for r in forensic_result["reasons"]
            if r != "No classical forensic anomalies detected in available signals"
            or not ai_reasons
        ]
        all_reasons = ai_reasons + forensic_reasons
        if not all_reasons:
            all_reasons = ["No anomalies detected by AI classifier or classical forensic signals"]

        # ── Stage 4: Attach AI result to forensic_signals for the report ──
        forensic_signals = forensic_result["forensic_signals"]
        forensic_signals["ai_classifier"] = ai_result

    except (VideoProcessingError, ValueError) as e:
        video.status = "failed"
        video.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=422, detail=f"Analysis failed: {e}")

    verdict, risk_level = _verdict_from_probability(final_fake_prob)
    confidence = _confidence_label(final_fake_prob)

    analysis = db.query(AnalysisResult).filter(AnalysisResult.video_id == video_id).first()
    if analysis is None:
        analysis = AnalysisResult(id=gen_uuid(), video_id=video_id)
        db.add(analysis)

    analysis.verdict = verdict
    analysis.fake_probability = final_fake_prob
    analysis.confidence_label = confidence
    analysis.risk_level = risk_level
    analysis.reasons = all_reasons
    analysis.timeline_segments = overlay_ai_on_timeline(
        forensic_result["timeline_segments"], 
        ai_result, 
        interval_ms=settings.frame_interval_ms
    )
    analysis.forensic_signals = forensic_signals
    analysis.model_used = model_used

    video.status = "analyzed"
    db.commit()
    db.refresh(analysis)

    return AnalysisResponse.model_validate(analysis)
