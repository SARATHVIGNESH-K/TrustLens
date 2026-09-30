"""
Video processing service.

Two responsibilities:
  1. extract_metadata()  — shell out to ffprobe for codec/fps/duration/etc.
  2. extract_frames()    — use OpenCV to pull frames at a fixed time interval.

Kept dependency-light (stdlib subprocess + OpenCV) so it doesn't need the full
FastAPI stack to run or be unit tested.
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2

logger = logging.getLogger("trustlens.video_processor")


@dataclass
class VideoMetadata:
    duration_sec: float | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    codec: str | None = None
    bitrate: int | None = None
    frame_count: int | None = None
    creation_time: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class VideoProcessingError(Exception):
    pass


def extract_frames_array(
    video_path: str | Path,
    interval_ms: int = 100,
    max_frames: int = 300,
) -> list:
    """
    Like extract_frames(), but returns frames as in-memory numpy arrays
    instead of writing JPEGs to disk. Used for dense sampling (e.g. every
    100ms) needed for blink/lip-sync detection, where saving every sampled
    frame to disk would bloat the frames directory used for the UI filmstrip.
    """
    video_path = str(video_path)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise VideoProcessingError(f"OpenCV could not open video: {video_path}")

    frames = []
    next_capture_ms = 0.0

    try:
        while len(frames) < max_frames:
            cap.set(cv2.CAP_PROP_POS_MSEC, next_capture_ms)
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
            next_capture_ms += interval_ms
    finally:
        cap.release()

    return frames


def extract_audio_wav(video_path: str | Path, output_path: str | Path) -> Path | None:
    """
    Extracts mono 16kHz PCM audio from the video via ffmpeg for lip-sync
    analysis. Returns None (instead of raising) if the video has no audio
    stream — that's a normal case, not an error.
    """
    video_path = str(video_path)
    output_path = Path(output_path)
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-f", "wav",
        str(output_path),
        "-loglevel", "error",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None

    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size < 100:
        return None
    return output_path


def extract_metadata(video_path: str | Path) -> VideoMetadata:
    """
    Run ffprobe against the video and parse out the fields TrustLens cares about.
    Raises VideoProcessingError if ffprobe fails or the file has no video stream.
    """
    video_path = str(video_path)
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError as e:
        raise VideoProcessingError("ffprobe is not installed or not on PATH") from e
    except subprocess.TimeoutExpired as e:
        raise VideoProcessingError("ffprobe timed out reading video metadata") from e

    if result.returncode != 0:
        raise VideoProcessingError(f"ffprobe failed: {result.stderr.strip()}")

    try:
        probe = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise VideoProcessingError("Could not parse ffprobe output") from e

    video_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None
    )
    if video_stream is None:
        raise VideoProcessingError("No video stream found in file")

    fmt = probe.get("format", {})

    # fps often comes as a fraction string like "30000/1001"
    fps = None
    r_frame_rate = video_stream.get("r_frame_rate")
    if r_frame_rate and "/" in r_frame_rate:
        num, den = r_frame_rate.split("/")
        try:
            den_f = float(den)
            fps = round(float(num) / den_f, 3) if den_f else None
        except ValueError:
            fps = None

    duration = fmt.get("duration") or video_stream.get("duration")
    frame_count = video_stream.get("nb_frames")

    return VideoMetadata(
        duration_sec=float(duration) if duration else None,
        fps=fps,
        width=video_stream.get("width"),
        height=video_stream.get("height"),
        codec=video_stream.get("codec_name"),
        bitrate=int(fmt["bit_rate"]) if fmt.get("bit_rate") else None,
        frame_count=int(frame_count) if frame_count and str(frame_count).isdigit() else None,
        creation_time=(fmt.get("tags") or {}).get("creation_time"),
    )


def extract_frames(
    video_path: str | Path,
    output_dir: str | Path,
    interval_ms: int = 500,
    max_frames: int = 300,
) -> list[str]:
    """
    Extract one frame every `interval_ms` milliseconds using OpenCV and save
    them as JPEGs into output_dir. Returns the list of saved file paths.

    Capped at max_frames to keep long videos from exhausting disk/time.
    """
    video_path = str(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise VideoProcessingError(f"OpenCV could not open video: {video_path}")

    saved_paths: list[str] = []
    next_capture_ms = 0.0
    frame_idx = 0

    try:
        while len(saved_paths) < max_frames:
            cap.set(cv2.CAP_PROP_POS_MSEC, next_capture_ms)
            ok, frame = cap.read()
            if not ok:
                break

            out_path = output_dir / f"frame_{frame_idx:05d}_{int(next_capture_ms)}ms.jpg"
            cv2.imwrite(str(out_path), frame)
            saved_paths.append(str(out_path))

            frame_idx += 1
            next_capture_ms += interval_ms
    finally:
        cap.release()

    if not saved_paths:
        raise VideoProcessingError("No frames could be extracted from the video")

    logger.info("Extracted %d frames from %s", len(saved_paths), video_path)
    return saved_paths
