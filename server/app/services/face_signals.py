"""
Face-based forensic signals — the deepfake-specific checks the generic
frame-level signals in forensics.py can't catch.

Uses OpenCV's bundled Haar cascade detectors (no model download required,
unlike Mediapipe's newer Tasks API) — cruder than landmark-based detection,
but dependency-light and works offline out of the box.

Implemented:
  - blink analysis            : face+eye cascade per dense frame -> blink rate
  - face-region optical flow  : does the face move consistently with the
                                 rest of the frame, or independently (a sign
                                 of a composited/warped face region)?
  - lip-sync correlation      : does mouth-region motion correlate with the
                                 audio envelope, or lag/decouple from it?

All three degrade gracefully (return a "not available" result rather than
raising) when no face is detected or no audio track exists — those are
normal cases, not errors.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

_FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
_EYE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

try:
    import mediapipe as mp
    _MP_FACE_MESH = mp.solutions.face_mesh
except Exception:
    _MP_FACE_MESH = None

_LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]


def _calc_ear(landmarks, indices, img_w, img_h) -> float:
    pts = np.array([[landmarks[i].x * img_w, landmarks[i].y * img_h] for i in indices], dtype=np.float32)
    v1 = np.linalg.norm(pts[1] - pts[5])
    v2 = np.linalg.norm(pts[2] - pts[4])
    h = np.linalg.norm(pts[0] - pts[3])
    return float((v1 + v2) / (2.0 * h + 1e-6))


def _detect_face(gray: np.ndarray):
    """Returns the largest detected face bbox (x, y, w, h) or None."""
    faces = _FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        return None
    # Largest face by area — assume the primary subject
    return max(faces, key=lambda f: f[2] * f[3])


def _count_eyes(gray: np.ndarray, face_bbox) -> int:
    x, y, w, h = face_bbox
    # Eyes sit in the upper ~60% of the face box; searching the whole face
    # box risks false positives from nostrils/mouth shadows.
    roi = gray[y: y + int(h * 0.6), x: x + w]
    eyes = _EYE_CASCADE.detectMultiScale(roi, scaleFactor=1.1, minNeighbors=6, minSize=(15, 15))
    return len(eyes)


def _count_blinks(eyes_per_frame: list) -> int:
    """
    Counts blink events: a run of frames with 0 eyes detected, bracketed by
    frames with >0 eyes detected on both sides (distinguishes a genuine
    blink from the face simply turning away or leaving frame, where the
    "0 eyes" run wouldn't be bracketed by a detected-eyes frame after it).
    """
    blink_count = 0
    i = 0
    n = len(eyes_per_frame)
    while i < n:
        if eyes_per_frame[i] == 0:
            j = i
            while j < n and eyes_per_frame[j] == 0:
                j += 1
            has_open_before = i > 0 and (eyes_per_frame[i - 1] or 0) > 0
            has_open_after = j < n and (eyes_per_frame[j] or 0) > 0
            if has_open_before and has_open_after:
                blink_count += 1
            i = j
        else:
            i += 1
    return blink_count


def analyze_blinking(frames: list[np.ndarray], interval_ms: int) -> dict:
    """
    Tracks eye closure per frame across a densely-sampled frame set
    and counts blink events. Uses MediaPipe FaceMesh EAR (Eye Aspect Ratio)
    when available for landmark-precision tracking, and gracefully falls back
    to OpenCV Haar cascades if unavailable or unindexed.
    """
    if not frames:
        return {"available": False, "reason": "no frames provided"}

    eyes_per_frame = []
    face_present = []
    detector_used = "haar_cascade"

    # Attempt MediaPipe FaceMesh first (superior accuracy and orientation invariance)
    if _MP_FACE_MESH is not None:
        try:
            with _MP_FACE_MESH.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            ) as fm:
                mp_eyes = []
                mp_present = []
                for frame in frames:
                    h, w = frame.shape[:2]
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    res = fm.process(rgb)
                    if not res.multi_face_landmarks:
                        mp_present.append(False)
                        mp_eyes.append(None)
                    else:
                        lms = res.multi_face_landmarks[0].landmark
                        ear_l = _calc_ear(lms, _LEFT_EYE_INDICES, w, h)
                        ear_r = _calc_ear(lms, _RIGHT_EYE_INDICES, w, h)
                        mean_ear = (ear_l + ear_r) / 2.0
                        mp_present.append(True)
                        # EAR < 0.20 indicates closed eyes; >= 0.20 indicates open
                        mp_eyes.append(0 if mean_ear < 0.20 else 2)

                if sum(mp_present) >= max(5, len(frames) * 0.3):
                    eyes_per_frame = mp_eyes
                    face_present = mp_present
                    detector_used = "mediapipe_facemesh"
        except Exception:
            pass

    # Fallback to OpenCV Haar cascade if MediaPipe didn't produce enough frames
    if not eyes_per_frame:
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face = _detect_face(gray)
            if face is None:
                face_present.append(False)
                eyes_per_frame.append(None)
                continue
            face_present.append(True)
            eyes_per_frame.append(_count_eyes(gray, face))

    frames_with_face = sum(face_present)
    if frames_with_face < max(5, len(frames) * 0.3):
        return {
            "available": False,
            "reason": "face not reliably detected across enough frames for blink analysis",
            "frames_with_face": frames_with_face,
            "frames_total": len(frames),
        }

    # Count blink events using the standalone helper
    blink_count = _count_blinks(eyes_per_frame)

    duration_sec = (len(frames) * interval_ms) / 1000.0
    blink_rate_per_min = (blink_count / duration_sec) * 60 if duration_sec > 0 else 0.0

    # Normal spontaneous human blink rate while awake/speaking is ~10-18/min.
    # Short clips (< 8 seconds) frequently exhibit zero blinks without being synthetic.
    # Only flag if duration with face is at least 8.0s and zero blinks occurred.
    flagged = duration_sec >= 8.0 and blink_count == 0

    return {
        "available": True,
        "blink_count": blink_count,
        "duration_sec": round(duration_sec, 2),
        "blink_rate_per_min": round(blink_rate_per_min, 1),
        "frames_with_face": frames_with_face,
        "frames_total": len(frames),
        "detector_used": detector_used,
        "flagged": flagged,
    }


def analyze_face_region_motion(frames: list[np.ndarray]) -> dict:
    """
    Computes dense optical flow between consecutive frames and compares
    motion magnitude inside the detected face box vs. the rest of the frame.
    A face that moves in a pattern uncorrelated with the background (while
    the background itself has real motion) can indicate a composited or
    independently-warped face region.
    """
    if len(frames) < 2:
        return {"available": False, "reason": "not enough frames"}

    face_mags = []
    bg_mags = []
    prev_gray = None
    last_face_bbox = None

    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face = _detect_face(gray)
        if face is not None:
            last_face_bbox = face

        if prev_gray is not None and last_face_bbox is not None:
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

            x, y, w, h = last_face_bbox
            face_mask = np.zeros_like(mag, dtype=bool)
            face_mask[y: y + h, x: x + w] = True

            face_mag = float(mag[face_mask].mean()) if face_mask.any() else 0.0
            bg_mag = float(mag[~face_mask].mean()) if (~face_mask).any() else 0.0
            face_mags.append(face_mag)
            bg_mags.append(bg_mag)

        prev_gray = gray

    if len(face_mags) < 3:
        return {"available": False, "reason": "face not detected consistently enough"}

    face_arr = np.array(face_mags)
    bg_arr = np.array(bg_mags)

    # Correlation between face-region and background motion magnitude
    # over time. Low/negative correlation while background has genuine
    # motion suggests the face isn't moving consistently with the scene.
    if face_arr.std() > 1e-6 and bg_arr.std() > 1e-6:
        correlation = float(np.corrcoef(face_arr, bg_arr)[0, 1])
    else:
        correlation = None

    bg_has_motion = float(bg_arr.mean()) > 0.15  # empirical low-motion floor

    flagged = bool(
        bg_has_motion and correlation is not None and correlation < 0.15
    )

    return {
        "available": True,
        "face_motion_mean": round(float(face_arr.mean()), 4),
        "background_motion_mean": round(float(bg_arr.mean()), 4),
        "face_background_correlation": round(correlation, 3) if correlation is not None else None,
        "flagged": flagged,
    }


def _audio_energy_envelope(wav_path: Path, num_samples: int, duration_sec: float) -> np.ndarray | None:
    """Reads a mono 16-bit PCM WAV and returns a short-time energy envelope
    resampled to `num_samples` points spanning `duration_sec`."""
    import wave

    try:
        with wave.open(str(wav_path), "rb") as wf:
            n_frames = wf.getnframes()
            sr = wf.getframerate()
            raw = wf.readframes(n_frames)
    except (wave.Error, FileNotFoundError, EOFError):
        return None

    if n_frames == 0:
        return None

    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if audio.size == 0:
        return None

    # Bucket audio samples into num_samples windows and take RMS energy per window
    total_samples = audio.size
    window = max(1, total_samples // max(num_samples, 1))
    envelope = []
    for i in range(num_samples):
        start = i * window
        end = min(start + window, total_samples)
        if start >= total_samples:
            envelope.append(0.0)
            continue
        chunk = audio[start:end]
        rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2))) if chunk.size else 0.0
        envelope.append(rms)

    return np.array(envelope)


def analyze_lip_sync(frames: list[np.ndarray], wav_path: Path | None, interval_ms: int) -> dict:
    """
    Proxies "mouth motion" as frame-to-frame pixel change in the lower third
    of the detected face box, and cross-correlates it against the audio
    energy envelope to find the best-aligning lag. A large lag or weak peak
    correlation suggests audio and mouth movement aren't well synchronized.
    """
    if wav_path is None:
        return {"available": False, "reason": "no audio track detected"}
    if len(frames) < 5:
        return {"available": False, "reason": "not enough frames"}

    mouth_motion = []
    prev_mouth_roi = None
    last_face_bbox = None

    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face = _detect_face(gray)
        if face is not None:
            last_face_bbox = face

        if last_face_bbox is None:
            mouth_motion.append(0.0)
            prev_mouth_roi = None
            continue

        x, y, w, h = last_face_bbox
        mouth_roi = gray[y + int(h * 0.6): y + h, x: x + w]

        if prev_mouth_roi is not None and prev_mouth_roi.shape == mouth_roi.shape:
            diff = float(np.mean(cv2.absdiff(mouth_roi, prev_mouth_roi)))
        else:
            diff = 0.0
        mouth_motion.append(diff)
        prev_mouth_roi = mouth_roi

    mouth_arr = np.array(mouth_motion)
    if mouth_arr.std() < 1e-6:
        return {"available": False, "reason": "no detectable mouth motion (face not tracked consistently)"}

    duration_sec = (len(frames) * interval_ms) / 1000.0
    audio_env = _audio_energy_envelope(wav_path, len(frames), duration_sec)
    if audio_env is None or audio_env.std() < 1e-6:
        return {"available": False, "reason": "could not extract usable audio envelope"}

    # Normalize both series and cross-correlate over a ±500ms lag window
    mouth_norm = (mouth_arr - mouth_arr.mean()) / (mouth_arr.std() + 1e-8)
    audio_norm = (audio_env - audio_env.mean()) / (audio_env.std() + 1e-8)

    max_lag_frames = max(1, int(500 / interval_ms))
    best_corr = -2.0
    best_lag = 0
    for lag in range(-max_lag_frames, max_lag_frames + 1):
        if lag >= 0:
            a, b = mouth_norm[lag:], audio_norm[: len(audio_norm) - lag]
        else:
            a, b = mouth_norm[: len(mouth_norm) + lag], audio_norm[-lag:]
        n = min(len(a), len(b))
        if n < 4:
            continue
        corr = float(np.corrcoef(a[:n], b[:n])[0, 1])
        if not np.isnan(corr) and corr > best_corr:
            best_corr = corr
            best_lag = lag

    lag_ms = best_lag * interval_ms
    # Genuine lip-sync anomaly occurs when there is active mouth motion and speech,
    # but the alignment lags significantly (|lag_ms| > 250ms with a solid peak > 0.25)
    # OR the motion is consistently out of phase with audio energy (best_corr < -0.25).
    # Near-zero correlation (e.g. -0.15 to 0.15) indicates ambient sound, music, or non-speech pauses.
    flagged = (abs(lag_ms) > 250 and best_corr > 0.25) or (best_corr < -0.25)

    return {
        "available": True,
        "best_correlation": round(best_corr, 3),
        "best_lag_ms": lag_ms,
        "flagged": flagged,
    }
