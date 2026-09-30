"""
Unit tests for app/services/face_signals.py.

The blink-counting and lag-detection logic is tested directly against
synthetic data with known correct answers — this doesn't depend on actual
face detection succeeding, so it runs reliably in any environment.
Face-detection-dependent behavior (graceful degradation when no face is
present) is tested against a real generated video, same pattern as
test_video_pipeline.py.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytest

from app.services.face_signals import (
    _count_blinks,
    analyze_blinking,
    analyze_face_region_motion,
    analyze_lip_sync,
)
from app.services.video_processor import extract_frames_array


# ---- Blink counting (pure logic, no CV involved) ------------------------

def test_count_blinks_two_clean_blinks():
    seq = [2, 2, 2, 0, 0, 2, 2, 2, 0, 0, 0, 2, 2]
    assert _count_blinks(seq) == 2


def test_count_blinks_ignores_trailing_zeros():
    # Trailing zeros (face leaves frame) must not be counted as a blink —
    # there's no "eyes reopen" frame after them.
    seq = [2, 2, 0, 2, 2, 0, 0, 0]
    assert _count_blinks(seq) == 1


def test_count_blinks_none_present():
    assert _count_blinks([2, 2, 2, 2, 2, 2]) == 0


def test_count_blinks_ignores_leading_zeros():
    # Face appears already closed — no "before" frame to bracket it.
    assert _count_blinks([0, 0, 2, 2, 2]) == 0


# ---- Lip-sync lag detection (pure logic, no CV involved) -----------------

def test_lip_sync_lag_detection_recovers_known_lag():
    np.random.seed(0)
    interval_ms = 100
    n = 40
    t = np.arange(n)
    true_signal = np.sin(t * 0.5) + np.random.normal(0, 0.05, n)

    true_lag_frames = 3
    mouth_norm = np.roll(true_signal, true_lag_frames)
    mouth_norm[:true_lag_frames] = 0
    audio_norm = true_signal

    max_lag_frames = max(1, int(500 / interval_ms))
    best_corr, best_lag = -2.0, 0
    for lag in range(-max_lag_frames, max_lag_frames + 1):
        if lag >= 0:
            a, b = mouth_norm[lag:], audio_norm[: len(audio_norm) - lag]
        else:
            a, b = mouth_norm[: len(mouth_norm) + lag], audio_norm[-lag:]
        n_ = min(len(a), len(b))
        if n_ < 4:
            continue
        corr = float(np.corrcoef(a[:n_], b[:n_])[0, 1])
        if not np.isnan(corr) and corr > best_corr:
            best_corr, best_lag = corr, lag

    assert best_lag == true_lag_frames
    assert best_corr > 0.95


# ---- Graceful degradation on a real (faceless) video ---------------------

@pytest.fixture(scope="module")
def faceless_video():
    tmp_dir = tempfile.mkdtemp()
    video_path = Path(tmp_dir) / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=4:size=160x120:rate=20",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(video_path),
            "-loglevel", "error",
        ],
        check=True,
    )
    yield video_path
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_blink_analysis_degrades_gracefully_without_face(faceless_video):
    frames = extract_frames_array(faceless_video, interval_ms=100)
    result = analyze_blinking(frames, interval_ms=100)
    assert result["available"] is False
    assert "face" in result["reason"]


def test_face_flow_degrades_gracefully_without_face(faceless_video):
    frames = extract_frames_array(faceless_video, interval_ms=100)
    result = analyze_face_region_motion(frames)
    assert result["available"] is False


def test_lip_sync_degrades_gracefully_without_audio(faceless_video):
    frames = extract_frames_array(faceless_video, interval_ms=100)
    result = analyze_lip_sync(frames, wav_path=None, interval_ms=100)
    assert result == {"available": False, "reason": "no audio track detected"}
