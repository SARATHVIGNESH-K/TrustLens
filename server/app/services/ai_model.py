"""
ViT-based deepfake detection using ONNX Runtime.

Model: onnx-community/Deep-Fake-Detector-v2-Model-ONNX
Architecture: Vision Transformer (ViT-Base/16) fine-tuned on real vs. deepfake images.
Labels: 0=Realism (authentic), 1=Deepfake
Preprocessing: resize to 224x224, normalize to [-1, 1] (mean=0.5, std=0.5 in [0,1] space)

This module provides per-frame predictions and a video-level aggregate score.
It is loaded lazily on first use and degrades gracefully if the model file is absent.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("trustlens.ai_model")

# ---- Paths ------------------------------------------------------------------
_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "deepfake_vit.onnx"

# ---- Lazy session -----------------------------------------------------------
_session = None
_session_error: str | None = None


def _get_session():
    global _session, _session_error
    if _session is not None:
        return _session
    if _session_error is not None:
        return None
    if not _MODEL_PATH.exists():
        _session_error = f"Model file not found at {_MODEL_PATH}"
        logger.warning(_session_error)
        return None
    try:
        import onnxruntime as ort
        _session = ort.InferenceSession(
            str(_MODEL_PATH),
            providers=["CPUExecutionProvider"],
        )
        logger.info("Loaded deepfake ViT model from %s", _MODEL_PATH)
        return _session
    except Exception as exc:
        _session_error = str(exc)
        logger.warning("Failed to load deepfake ViT model: %s", exc)
        return None


# ---- Preprocessing ----------------------------------------------------------

def _preprocess_frame(frame_bgr: np.ndarray) -> np.ndarray | None:
    """Detect and crop face, then resize and normalize to (1, 3, 224, 224) float32 tensor."""
    from app.services.face_signals import _detect_face
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    face_bbox = _detect_face(gray)
    if face_bbox is None:
        return None
        
    x, y, w, h = face_bbox
    margin_x = int(w * 0.2)
    margin_y = int(h * 0.2)
    img_h, img_w = frame_bgr.shape[:2]
    
    x1 = max(0, x - margin_x)
    y1 = max(0, y - margin_y)
    x2 = min(img_w, x + w + margin_x)
    y2 = min(img_h, y + h + margin_y)
    
    face_crop = frame_bgr[y1:y2, x1:x2]

    rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_CUBIC)
    
    # ImageNet normalization expected by the ViT model
    img = resized.astype(np.float32) / 255.0
    mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    norm = (img - mean) / std
    
    return np.transpose(norm, (2, 0, 1))[np.newaxis, :]  # (1, 3, H, W)


def _softmax(logits: np.ndarray) -> np.ndarray:
    e = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def predict_frame(frame_bgr: np.ndarray) -> float | None:
    """
    Returns the probability (0.0–1.0) that a single frame is a deepfake,
    or None if the model is unavailable or no face is detected.
    """
    session = _get_session()
    if session is None:
        return None
    try:
        tensor = _preprocess_frame(frame_bgr)
        if tensor is None:
            return None
        logits = session.run(None, {"pixel_values": tensor})[0]
        probs = _softmax(logits)
        # The HF config wrongly maps 1=Deepfake. Based on standard ImageFolder 
        # alphabetical sorting (Deepfake, Realism), 0 is Deepfake.
        return float(probs[0][0])
    except Exception as exc:
        logger.warning("ViT inference error: %s", exc)
        return None


# ---- Video-level analysis ---------------------------------------------------

def analyze_video_frames(
    frame_paths: list[str],
    *,
    max_frames: int = 128,
) -> dict:
    """
    Runs the ViT deepfake classifier on up to `max_frames` evenly sampled
    frames from the video (reading from pre-extracted JPEG paths).

    Returns a dict:
      {
        "available": bool,
        "reason": str | None,          # if unavailable
        "fake_probability": float,     # 0-100 mean across top-k frames
        "frame_scores": list[float],   # per-frame deepfake probability (0-1)
        "max_frame_score": float,      # worst-case individual frame
        "high_risk_frame_count": int,  # frames with fake_prob > 0.65
        "model": "vit-deepfake-v2",
      }
    """
    session = _get_session()
    if session is None:
        return {
            "available": False,
            "reason": _session_error or "Model not loaded",
            "model": "vit-deepfake-v2",
        }

    if not frame_paths:
        return {
            "available": False,
            "reason": "No frames provided",
            "model": "vit-deepfake-v2",
        }

    # Evenly sample up to max_frames from the available paths
    indices = np.linspace(0, len(frame_paths) - 1, min(max_frames, len(frame_paths)), dtype=int)
    sampled = [frame_paths[i] for i in indices]

    frame_scores: list[float] = []
    sampled_timestamps_ms: list[int] = []
    sampled_frame_indices: list[int] = []
    for idx, path in zip(indices, sampled):
        frame_bgr = cv2.imread(path)
        if frame_bgr is None:
            continue
        score = predict_frame(frame_bgr)
        if score is None:
            continue
        frame_scores.append(score)
        sampled_frame_indices.append(int(idx))
        sampled_timestamps_ms.append(_timestamp_ms_from_path(path, int(idx)))

    if not frame_scores:
        return {
            "available": False,
            "reason": "No frames could be read or classified",
            "model": "vit-deepfake-v2",
        }

    # Focus on the high range to increase accuracy
    top_k = max(1, len(frame_scores) // 4) # Top 25% frames
    top_k_scores = sorted(frame_scores)[-top_k:]
    mean_fake_prob = float(np.mean(top_k_scores))
    
    max_frame_score = float(np.max(frame_scores))
    high_risk_count = int(sum(1 for s in frame_scores if s >= 0.65))

    return {
        "available": True,
        "fake_probability": round(mean_fake_prob * 100, 1),
        "frame_scores": [round(s, 3) for s in frame_scores],
        "sampled_timestamps_ms": sampled_timestamps_ms,
        "sampled_frame_indices": sampled_frame_indices,
        "max_frame_score": round(max_frame_score, 3),
        "high_risk_frame_count": high_risk_count,
        "total_frames_analyzed": len(frame_scores),
        "model": "vit-deepfake-v2",
    }


def _timestamp_ms_from_path(path: str, fallback_index: int) -> int:
    match = re.search(r"_(\d+)ms\.(?:jpg|jpeg|png)$", path.replace("\\", "/"), re.IGNORECASE)
    if match:
        return int(match.group(1))
    return fallback_index * 500


def generate_heatmap(frame_path: str, out_path: str) -> bool:
    """
    Generates an occlusion-based heatmap for the given frame and saves it.
    Uses a 7x7 grid over the 224x224 face region.
    Returns True if successful.
    """
    session = _get_session()
    if session is None:
        return False

    frame_bgr = cv2.imread(frame_path)
    if frame_bgr is None:
        return False

    from app.services.face_signals import _detect_face
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    face_bbox = _detect_face(gray)
    if face_bbox is None:
        return False

    x, y, w, h = face_bbox
    margin_x = int(w * 0.2)
    margin_y = int(h * 0.2)
    img_h, img_w = frame_bgr.shape[:2]
    
    x1 = max(0, x - margin_x)
    y1 = max(0, y - margin_y)
    x2 = min(img_w, x + w + margin_x)
    y2 = min(img_h, y + h + margin_y)
    
    face_crop = frame_bgr[y1:y2, x1:x2]
    rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_CUBIC)
    
    img = resized.astype(np.float32) / 255.0
    mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    std = np.array([0.5, 0.5, 0.5], dtype=np.float32)
    norm = (img - mean) / std
    
    base_tensor = np.transpose(norm, (2, 0, 1))[np.newaxis, :]  # (1, 3, 224, 224)
    
    try:
        base_logits = session.run(None, {"pixel_values": base_tensor})[0]
        base_prob = float(_softmax(base_logits)[0][0])
    except Exception:
        return False

    grid_size = 7
    patch_size = 224 // grid_size
    heatmap = np.zeros((grid_size, grid_size), dtype=np.float32)

    for i in range(grid_size):
        for j in range(grid_size):
            occluded_tensor = base_tensor.copy()
            # Occlude with 0 (which is the mean since we normalized with mean=0.5)
            y_start, y_end = i * patch_size, (i + 1) * patch_size
            x_start, x_end = j * patch_size, (j + 1) * patch_size
            occluded_tensor[0, :, y_start:y_end, x_start:x_end] = 0.0
            
            try:
                logits = session.run(None, {"pixel_values": occluded_tensor})[0]
                prob = float(_softmax(logits)[0][0])
                # Importance is how much the deepfake probability dropped
                heatmap[i, j] = max(0.0, base_prob - prob)
            except Exception:
                pass

    if np.max(heatmap) > 0:
        heatmap = heatmap / np.max(heatmap)

    heatmap_resized = cv2.resize(heatmap, (224, 224), interpolation=cv2.INTER_CUBIC)
    heatmap_colored = cv2.applyColorMap(np.uint8(255 * heatmap_resized), cv2.COLORMAP_JET)
    heatmap_colored_rgb = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
    
    # Use the heatmap itself as an alpha mask (max 60% opacity for the hot regions)
    # This prevents the entire face crop from being tinted blue where importance is 0.
    alpha = heatmap_resized[..., np.newaxis] * 0.6
    overlay = (resized * (1 - alpha) + heatmap_colored_rgb * alpha).astype(np.uint8)
    
    overlay_bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)
    
    # Resize back to original crop size and replace in full frame
    overlay_restored = cv2.resize(overlay_bgr, (x2 - x1, y2 - y1), interpolation=cv2.INTER_CUBIC)
    
    # Draw a bounding box for clarity
    cv2.rectangle(overlay_restored, (0, 0), (x2 - x1 - 1, y2 - y1 - 1), (0, 0, 255), 2)
    
    result_frame = frame_bgr.copy()
    result_frame[y1:y2, x1:x2] = overlay_restored
    
    cv2.imwrite(out_path, result_frame)
    return True


def is_available() -> bool:
    """Returns True if the ViT model is loaded and ready."""
    return _get_session() is not None
