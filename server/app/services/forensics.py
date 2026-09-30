"""
Classical digital-forensics signal extraction.

These are real, computable signals from the extracted frames — no trained
model required. They form the basis of the authenticity score until a
trained deepfake classifier (see app/services/ai_model.py, to be added) is
plugged in. Each function returns a plain float/dict so results are easy to
store as JSON and show in a report.

Implemented:
  - frame_difference_score   : mean inter-frame pixel change (motion/cut detector)
  - blur_variance             : Laplacian variance, flags unnaturally smooth/sharp frames
  - compression_artifact_score: block-edge energy typical of heavy re-encoding
  - brightness_consistency    : lighting stability across frames
  - combine_with_face_signals : merges in blink/face-motion/lip-sync signals
                                 computed by app.services.face_signals
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _load_gray(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Could not read frame: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def frame_difference_series(frame_paths: list[str]) -> list[float]:
    """Mean absolute pixel difference between consecutive frames (0-255 scale)."""
    diffs = []
    prev = None
    for p in frame_paths:
        gray = _load_gray(p)
        if prev is not None:
            diffs.append(float(np.mean(cv2.absdiff(gray, prev))))
        prev = gray
    return diffs


def blur_variance_series(frame_paths: list[str]) -> list[float]:
    """Laplacian variance per frame — low values indicate unnatural smoothing
    sometimes introduced by GAN upsampling / face-swap blending."""
    return [float(cv2.Laplacian(_load_gray(p), cv2.CV_64F).var()) for p in frame_paths]


def compression_artifact_score(frame_paths: list[str], block_size: int = 8) -> float:
    """
    Approximates JPEG/H.264 block-edge energy: heavy or repeated re-encoding
    leaves faint periodic edges at block boundaries (multiples of 8px).
    Returns a 0-1 score; higher means stronger block-edge signal.
    """
    scores = []
    for p in frame_paths:
        gray = _load_gray(p).astype(np.float32)
        h, w = gray.shape
        if h < block_size * 2 or w < block_size * 2:
            continue
        # Sum gradient magnitude exactly at block boundaries vs. elsewhere
        grad_x = np.abs(np.diff(gray, axis=1))
        boundary_cols = np.arange(block_size - 1, w - 1, block_size)
        if len(boundary_cols) == 0:
            continue
        boundary_energy = grad_x[:, boundary_cols].mean()
        overall_energy = grad_x.mean() + 1e-6
        scores.append(float(boundary_energy / overall_energy))
    if not scores:
        return 0.0
    # Normalize: ratio near 1.0 is "no special block edges", higher is suspicious
    raw = float(np.mean(scores))
    return float(np.clip((raw - 1.0), 0.0, 1.0))


def brightness_consistency(frame_paths: list[str]) -> dict:
    """Mean brightness per frame + coefficient of variation across the clip."""
    means = [float(np.mean(_load_gray(p))) for p in frame_paths]
    if not means:
        return {"mean": 0.0, "coefficient_of_variation": 0.0, "per_frame": []}
    mean_of_means = float(np.mean(means))
    std = float(np.std(means))
    cv_ = std / mean_of_means if mean_of_means else 0.0
    return {
        "mean": mean_of_means,
        "coefficient_of_variation": cv_,
        "per_frame": means,
    }


def noise_naturalness_score(frame_paths: list[str]) -> dict:
    """
    Estimates sensor-noise level per frame using the Immerkær (1996) fast
    noise estimation method — convolution with a Laplacian-like kernel
    specifically designed to suppress edge/structure content so it isn't
    confused with genuine high-frequency noise.

    (An earlier version of this used a plain Gaussian-blur residual, which
    was found during testing to conflate hard edges — e.g. sharp geometric
    boundaries in test patterns — with real noise, giving near-identical
    readings for both a noise-free and a deliberately noised version of the
    same footage. This estimator is far more edge-robust.)

    Compares the result against an absolute floor rather than comparing
    frames to each other, unlike the other signals in this module — real
    camera sensors almost always leave some noise texture; its near-total
    absence is itself a signal that the footage may be fully synthetic
    rather than a camera capture.

    Caveat (confirmed during testing, not just theoretical): heavy video
    compression — including ordinary H.264 encoding used by WhatsApp,
    YouTube, etc., not just deliberate re-editing — already strips out most
    of a real camera's noise floor. Testing this estimator against the same
    clip with and without deliberately injected noise showed nearly
    identical readings after H.264 encoding (noise was discarded by the
    compressor either way). That means this signal is most useful against
    high-quality/uncompressed footage and less discriminating on typical
    compressed consumer uploads, where real and synthetic footage can both
    land in a similar low-noise range. Treat as one signal among several,
    not a standalone verdict — and expect to recalibrate LOW_NOISE_THRESHOLD
    against real labeled data.
    """
    LOW_NOISE_THRESHOLD = 0.3  # Tuned down from 0.8 to accommodate H.264 compression

    # Laplacian-like kernel from Immerkær's method — a second-derivative
    # approximation that responds weakly to smooth edges/gradients but
    # strongly to true pixel-level noise.
    kernel = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float32)

    noise_sigmas = []
    for p in frame_paths:
        gray = _load_gray(p).astype(np.float32)
        h, w = gray.shape
        if h < 5 or w < 5:
            continue
        conv = cv2.filter2D(gray, -1, kernel, borderType=cv2.BORDER_REFLECT)
        sigma = float(np.sqrt(np.pi / 2) * np.mean(np.abs(conv)) / 6.0)
        noise_sigmas.append(sigma)

    if not noise_sigmas:
        return {"available": False, "reason": "no frames"}

    mean_noise_sigma = float(np.mean(noise_sigmas))
    flagged = mean_noise_sigma < LOW_NOISE_THRESHOLD

    return {
        "available": True,
        "mean_noise_sigma": round(mean_noise_sigma, 4),
        "threshold": LOW_NOISE_THRESHOLD,
        "flagged": flagged,
    }


def combine_with_face_signals(
    base_result: dict,
    blink_result: dict,
    face_flow_result: dict,
    lip_sync_result: dict,
) -> dict:
    """
    Merges face-specific signals (blink rate, face-region optical flow
    consistency, lip-sync correlation) into the base frame-level forensic
    result. These are deepfake-specific tells that the generic frame-level
    signals in run_forensic_analysis() can't catch on their own.

    Each signal only contributes if it was actually computable (a face was
    detected, audio existed, etc.) — unavailable signals are recorded in
    forensic_signals for transparency but don't move the score either way.
    """
    score = base_result["fake_probability"]
    reasons = [r for r in base_result["reasons"] if r != "No classical forensic anomalies detected in available signals"]

    if blink_result.get("available") and blink_result.get("flagged"):
        score += 20
        reasons.append(
            f"No eye blinks detected across {blink_result['duration_sec']}s of footage "
            "with a face present — natural human speech over this duration typically exhibits blinks"
        )

    if face_flow_result.get("available") and face_flow_result.get("flagged"):
        score += 15
        corr = face_flow_result.get("face_background_correlation")
        reasons.append(
            f"Face-region motion is poorly correlated with background motion "
            f"(correlation {corr}) despite background movement — possible composited "
            "or independently-warped face region"
        )

    if lip_sync_result.get("available") and lip_sync_result.get("flagged"):
        score += 15
        lag = lip_sync_result.get("best_lag_ms", 0)
        corr = lip_sync_result.get("best_correlation")
        reasons.append(
            f"Mouth motion does not track the audio track well (best correlation "
            f"{corr} at a {lag}ms offset) — possible lip-sync mismatch"
        )

    # If literally no reasons were ever added anywhere, keep the original
    # "no anomalies" message rather than leaving an empty list.
    if not reasons:
        reasons = ["No classical forensic anomalies detected in available signals"]

    fake_probability = float(np.clip(score, 0.0, 100.0))
    authenticity_score = round(max(0.0, min(100.0, 100.0 - fake_probability)), 1)

    forensic_signals = dict(base_result["forensic_signals"])
    forensic_signals["blink"] = blink_result
    forensic_signals["face_region_motion"] = face_flow_result
    forensic_signals["lip_sync"] = lip_sync_result

    return {
        **base_result,
        "fake_probability": round(fake_probability, 1),
        "authenticity_score": authenticity_score,
        "reasons": reasons,
        "forensic_signals": forensic_signals,
    }


def run_forensic_analysis(frame_paths: list[str], interval_ms: int = 500) -> dict:
    """
    Runs all available classical checks and returns a structured result:
      - raw signals (for the report / debugging)
      - a heuristic 0-100 fake-probability score and authenticity score
      - human-readable reasons
      - a suspicious timeline segmented at interval boundaries

    Calibrated to avoid false positives on standard camera motion,
    everyday H.264 video compression, and natural lighting shifts.
    """
    if len(frame_paths) < 2:
        raise ValueError("Need at least 2 frames to run forensic analysis")

    frame_diffs = frame_difference_series(frame_paths)
    blur_vals = blur_variance_series(frame_paths)
    compression_score = compression_artifact_score(frame_paths)
    brightness = brightness_consistency(frame_paths)
    noise_result = noise_naturalness_score(frame_paths)

    reasons: list[str] = []
    suspicion_points: list[float] = [0.0] * len(frame_diffs)  # aligned to transitions i->i+1

    # Signal 1: sudden frame-difference spikes (possible splice / face-swap seam)
    if frame_diffs:
        mean_diff = float(np.mean(frame_diffs))
        std_diff = float(np.std(frame_diffs)) or 1e-6
        median_diff = float(np.median(frame_diffs)) or 1e-6
        spike_indices = []
        for i, d in enumerate(frame_diffs):
            z = (d - mean_diff) / std_diff
            # True splicing/seam requires outlier z > 3.0, substantial absolute diff > 16.0,
            # and noticeably higher than median difference
            if z > 3.0 and d > 16.0 and d > 2.5 * median_diff:
                suspicion_points[i] += 0.4
                spike_indices.append(i)
        spike_count = len(spike_indices)
        if spike_count:
            reasons.append(
                f"{spike_count} abrupt frame-to-frame change spike(s) detected — "
                "consistent with splice points or face-region replacement"
            )

    # Signal 2: unnaturally low blur variance (over-smoothed synthetic regions)
    if blur_vals:
        median_blur = float(np.median(blur_vals))
        if median_blur > 50.0:
            low_blur_frames = [i for i, b in enumerate(blur_vals) if b < median_blur * 0.25]
            if len(low_blur_frames) >= max(3, int(len(blur_vals) * 0.2)):
                reasons.append(
                    "Multiple frames show unusually low high-frequency detail — "
                    "possible GAN-smoothed or blended facial region"
                )
                for i in low_blur_frames:
                    if i < len(suspicion_points):
                        suspicion_points[i] += 0.3

    # Signal 3: compression block-edge anomaly
    if compression_score > 0.30:
        reasons.append(
            f"Block-edge compression artifacts stronger than expected "
            f"(score {compression_score:.2f}) — suggests re-encoding after editing"
        )

    # Signal 4: lighting inconsistency
    if brightness["coefficient_of_variation"] > 0.35:
        reasons.append(
            "Brightness fluctuates substantially across the clip — "
            "possible inconsistent lighting between original and inserted content"
        )

    # Signal 5: absolute noise floor
    if noise_result.get("available") and noise_result.get("flagged"):
        reasons.append(
            f"Footage shows unusually low sensor noise (estimated sigma "
            f"{noise_result['mean_noise_sigma']}, expected above "
            f"{noise_result['threshold']}) — potential synthetic smoothing, "
            "though standard H.264 compression can also contribute"
        )

    if not reasons:
        reasons.append("No classical forensic anomalies detected in available signals")

    # Aggregate heuristic score (0-100).
    spike_penalty = min(30.0, (sum(suspicion_points) / max(len(suspicion_points), 1)) * 60)
    comp_penalty = max(0.0, (compression_score - 0.20)) * 25.0
    light_penalty = max(0.0, (brightness["coefficient_of_variation"] - 0.30)) * 25.0
    noise_penalty = 5.0 if (noise_result.get("available") and noise_result.get("flagged")) else 0.0

    base = spike_penalty + comp_penalty + light_penalty + noise_penalty
    fake_probability = float(np.clip(base, 0.0, 100.0))
    authenticity_score = round(max(0.0, min(100.0, 100.0 - fake_probability)), 1)

    # Build a coarse timeline grouped into 1-second bins
    timeline = []
    interval_s = interval_ms / 1000.0
    bins_scores: dict[int, float] = {}
    for i, score in enumerate(suspicion_points):
        t = int((i + 0.5) * interval_s)
        bins_scores[t] = max(bins_scores.get(t, 0.0), score)

    max_t = max(bins_scores.keys(), default=-1)
    for t in range(0, max_t + 1):
        score = bins_scores.get(t, 0.0)
        status = "suspicious" if score >= 0.35 else "normal"
        seg_reason = (
            "Elevated frame change and/or texture anomaly in this segment"
            if status == "suspicious"
            else "No anomaly detected in this segment"
        )
        timeline.append({"start": t, "end": t + 1, "status": status, "reason": seg_reason})

    merged = merge_adjacent_segments(timeline)

    return {
        "fake_probability": round(fake_probability, 1),
        "authenticity_score": authenticity_score,
        "reasons": reasons,
        "timeline_segments": merged,
        "forensic_signals": {
            "frame_diff_mean": float(np.mean(frame_diffs)) if frame_diffs else None,
            "blur_variance_median": float(np.median(blur_vals)) if blur_vals else None,
            "compression_artifact_score": compression_score,
            "brightness": brightness,
            "noise_naturalness": noise_result,
        },
        "model_used": "forensics-heuristic-v1",
    }


def merge_adjacent_segments(timeline: list[dict]) -> list[dict]:
    """Collapse neighboring segments that share the same status."""
    merged: list[dict] = []
    for seg in timeline:
        item = dict(seg)
        if merged and merged[-1]["status"] == item["status"] and merged[-1]["end"] >= item["start"]:
            merged[-1]["end"] = max(merged[-1]["end"], item["end"])
            if item["status"] == "suspicious" and "ViT" in item.get("reason", ""):
                merged[-1]["reason"] = item["reason"]
        else:
            merged.append(item)
    return merged


def overlay_ai_on_timeline(
    timeline: list[dict],
    ai_result: dict,
    *,
    interval_ms: int = 500,
) -> list[dict]:
    """
    Paint ViT per-frame scores onto the forensic timeline.

    Classical splice/blur checks often stay quiet on fully synthetic clips,
    which used to leave a green "no anomalies" bar next to a high deepfake
    percentage. Any sampled frame at or above 0.45 fake-prob flags its
    time window; if the clip-level AI score is still elevated and nothing
    was painted, the whole span is marked suspicious.
    """
    if not ai_result or not ai_result.get("available"):
        return merge_adjacent_segments([dict(s) for s in timeline]) if timeline else timeline

    scores = ai_result.get("frame_scores") or []
    timestamps_ms = ai_result.get("sampled_timestamps_ms") or []
    if len(timestamps_ms) != len(scores):
        timestamps_ms = [int(i * interval_ms) for i in range(len(scores))]

    mean_pct = float(ai_result.get("fake_probability") or 0.0)
    frame_flag = 0.45

    flagged: list[tuple[int, float]] = [
        (int(ts), float(score)) for ts, score in zip(timestamps_ms, scores) if score >= frame_flag
    ]

    if mean_pct >= 45 and not flagged and scores:
        cutoff = max(float(np.median(scores)), 0.35)
        flagged = [
            (int(ts), float(score))
            for ts, score in zip(timestamps_ms, scores)
            if score >= cutoff
        ]

    if not timeline:
        if not flagged and mean_pct < 45:
            return []
        span_end = 1
        if timestamps_ms:
            span_end = max(1, int(np.ceil(max(timestamps_ms) / 1000.0)) + 1)
        timeline = [{
            "start": 0,
            "end": span_end,
            "status": "normal",
            "reason": "No anomaly detected in this segment",
        }]

    start = int(min(s["start"] for s in timeline))
    end = int(max(s["end"] for s in timeline))
    if end <= start:
        end = start + 1

    bins: list[dict] = []
    for t in range(start, end):
        covering = next(
            (s for s in timeline if s["start"] <= t < s["end"]),
            timeline[-1],
        )
        bins.append({
            "start": t,
            "end": t + 1,
            "status": covering["status"],
            "reason": covering["reason"],
        })

    def _flag_bin(bin_seg: dict, score: float) -> None:
        bin_seg["status"] = "suspicious"
        bin_seg["reason"] = (
            f"ViT classifier scored this region {score:.0%} likely synthetic"
        )

    painted = False
    for ts, score in flagged:
        t_sec = ts / 1000.0
        for bin_seg in bins:
            if bin_seg["start"] <= t_sec < bin_seg["end"] or (
                t_sec >= bin_seg["start"] and t_sec <= bin_seg["end"] and bin_seg["end"] == end
            ):
                _flag_bin(bin_seg, score)
                painted = True
                break
        else:
            # Timestamp sits past the last forensic bin (rounding) — extend.
            last = bins[-1]
            if t_sec >= last["end"]:
                _flag_bin(last, score)
                painted = True

    if mean_pct >= 45 and not painted:
        for bin_seg in bins:
            _flag_bin(bin_seg, mean_pct / 100.0)
            bin_seg["reason"] = (
                f"ViT classifier flagged the clip as synthetic "
                f"(mean fake probability {mean_pct:.0f}%)"
            )

    return merge_adjacent_segments(bins)
