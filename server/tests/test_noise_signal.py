"""
Unit tests for noise_naturalness_score() in app/services/forensics.py.

Uses hand-built controlled images (flat regions, isolated edges) rather than
real photos, so the tests cleanly isolate "is this responding to noise" from
"is this responding to edges/structure" — the exact distinction that matters
for this estimator (see the function's docstring for why a naive
Gaussian-blur-residual approach was rejected in favor of the Immerkær
method).
"""
import numpy as np
import cv2
import pytest

from app.services.forensics import noise_naturalness_score


@pytest.fixture
def img_dir(tmp_path):
    return tmp_path


def _save(path, array):
    cv2.imwrite(str(path), array, [cv2.IMWRITE_JPEG_QUALITY, 100])
    return str(path)


def test_flat_clean_image_reads_near_zero(img_dir):
    flat = np.full((120, 160), 128, dtype=np.uint8)
    path = _save(img_dir / "flat.jpg", flat)
    result = noise_naturalness_score([path, path])
    assert result["available"] is True
    assert result["mean_noise_sigma"] < 0.2
    assert result["flagged"] is True


def test_flat_image_with_real_noise_is_not_flagged(img_dir):
    rng = np.random.default_rng(0)
    noisy = np.clip(128 + rng.normal(0, 6, (120, 160)), 0, 255).astype(np.uint8)
    path = _save(img_dir / "noisy.jpg", noisy)
    result = noise_naturalness_score([path, path])
    assert result["available"] is True
    assert result["mean_noise_sigma"] > result["threshold"]
    assert result["flagged"] is False


def test_moderate_scale_hard_edge_is_not_confused_with_high_noise(img_dir):
    # A single large hard edge (like a real object boundary) should NOT
    # register as high noise the way per-pixel-alternating patterns would —
    # this is the key edge-robustness property vs. a naive blur-residual.
    half = np.zeros((120, 160), dtype=np.uint8)
    half[:, 80:] = 255
    path = _save(img_dir / "half_edge.jpg", half)
    result = noise_naturalness_score([path, path])
    assert result["available"] is True
    # A flat region with one hard edge and zero real noise correctly reads
    # as very low noise, same as the plain flat case.
    assert result["mean_noise_sigma"] < 0.5


def test_empty_frame_list_returns_unavailable():
    result = noise_naturalness_score([])
    assert result == {"available": False, "reason": "no frames"}
