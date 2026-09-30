"""
Unit tests for the video processing and forensics pipeline.

These use ffmpeg's `testsrc` filter to generate a tiny synthetic video at
test time, so tests are self-contained and don't need a sample asset checked
into the repo. Run with: pytest tests/
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.services.video_processor import extract_metadata, extract_frames, VideoProcessingError
from app.services.forensics import run_forensic_analysis


@pytest.fixture(scope="module")
def sample_video():
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


def test_extract_metadata_returns_expected_fields(sample_video):
    meta = extract_metadata(sample_video)
    assert meta.duration_sec == pytest.approx(4.0, abs=0.2)
    assert meta.fps == pytest.approx(20.0, abs=0.1)
    assert meta.width == 160
    assert meta.height == 120
    assert meta.codec == "h264"


def test_extract_metadata_missing_file_raises():
    with pytest.raises(VideoProcessingError):
        extract_metadata("/nonexistent/path/video.mp4")


def test_extract_frames_respects_interval(sample_video, tmp_path):
    frames = extract_frames(sample_video, tmp_path, interval_ms=500)
    # 4 seconds / 0.5s interval -> ~8 frames
    assert 6 <= len(frames) <= 9
    for p in frames:
        assert Path(p).exists()


def test_extract_frames_caps_at_max_frames(sample_video, tmp_path):
    frames = extract_frames(sample_video, tmp_path, interval_ms=100, max_frames=5)
    assert len(frames) == 5


def test_forensic_analysis_returns_structured_result(sample_video, tmp_path):
    frames = extract_frames(sample_video, tmp_path, interval_ms=500)
    result = run_forensic_analysis(frames, interval_ms=500)

    assert 0.0 <= result["fake_probability"] <= 100.0
    assert isinstance(result["reasons"], list) and len(result["reasons"]) > 0
    assert isinstance(result["timeline_segments"], list) and len(result["timeline_segments"]) > 0
    for seg in result["timeline_segments"]:
        assert seg["status"] in ("normal", "suspicious")
        assert seg["end"] > seg["start"]
    assert result["model_used"] == "forensics-heuristic-v1"


def test_forensic_analysis_requires_at_least_two_frames():
    with pytest.raises(ValueError):
        run_forensic_analysis(["only_one_frame.jpg"], interval_ms=500)
