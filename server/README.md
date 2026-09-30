# TrustLens — Server

FastAPI backend: video upload, metadata/frame extraction, and classical
digital-forensics analysis. No trained AI model is wired in yet (see
"AI model" section below) — analysis currently runs on real, computable
forensic signals rather than a placeholder/random score.

## What's implemented

| Endpoint | Method | Description |
|---|---|---|
| `/api/upload` | POST | Upload a video, extract metadata via `ffprobe` |
| `/api/analyze/{video_id}` | POST | Extract frames, run forensic analysis, store results |
| `/api/history` | GET | List all analyzed videos |
| `/api/history/{video_id}` | DELETE | Delete a video and its files |
| `/api/report/{video_id}` | GET | Full video + analysis detail |
| `/api/stats` | GET | Aggregate dashboard numbers |
| `/api/health` | GET | Health check |

Not yet implemented: `/api/login`, `/api/signup` (auth), PDF report export,
admin endpoints, trained AI model + Grad-CAM/SHAP.

## Forensic signals currently computed

Frame-level (generic, every video):
- **Frame-difference spikes** — abrupt inter-frame change, a proxy for splice points
- **Blur variance** — unnaturally smooth regions (possible GAN blending)
- **Compression block-edge score** — re-encoding artifacts
- **Brightness consistency** — lighting stability across the clip

Face-specific (deepfake-targeted, requires a detectable face / audio track):
- **Blink rate** — Haar-cascade eye detection across a densely-sampled
  (100ms interval) frame set; flags a total absence of blinks over a clip
  long enough that a real subject would almost certainly blink at least once
- **Face-region optical flow consistency** — compares motion inside the
  detected face box against the rest of the frame; a face moving
  independently of real background motion suggests a composited/warped
  region
- **Lip-sync correlation** — extracts the audio envelope and cross-correlates
  it against mouth-region motion to find the best-aligning lag; a weak
  correlation or large lag suggests audio/video desync

The face-specific checks use OpenCV's bundled Haar cascade detectors (no
model download required) rather than landmark-based detection (e.g.
Mediapipe's Face Landmarker) — cruder, but works offline with zero extra
setup. All three degrade gracefully (reported as `"available": false` with
a reason, not an error) when no face is detected or no audio track exists.

These are real OpenCV/numpy computations against actual extracted frames —
verified against generated test video during development (see
`tests/test_video_pipeline.py` and `tests/test_face_signals.py`). They're a
reasonable first pass but are **not** a substitute for a trained deepfake
classifier; treat the resulting score as a heuristic signal, not a
certified verdict.

## Setup

Requires **Python 3.10+** and **ffmpeg** installed and on your PATH.

```bash
cd server
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Verify ffmpeg is installed:

```bash
ffmpeg -version
ffprobe -version
```

If missing on Windows: download from https://ffmpeg.org/download.html,
extract, and add the `bin` folder to your PATH. On macOS: `brew install ffmpeg`.
On Ubuntu/Debian: `sudo apt install ffmpeg`.

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive Swagger API docs.

The frontend's Vite dev server proxies `/api/*` to `http://localhost:8000`
(see `client/vite.config.js`), so once both are running, the React app's
mock data can be swapped for real `axios` calls with no CORS setup needed.

## Test

```bash
pip install pytest
pytest tests/ -v
```

Tests generate a small synthetic video with `ffmpeg`'s `testsrc` filter at
run time — no fixture files needed.

## AI model — not yet plugged in

The spec calls for a trained deepfake classifier (EfficientNet/ViT) with
Grad-CAM/SHAP explanations. This sandbox has no internet access to fetch
model weights, so that piece isn't built yet. When you're ready:

1. Get a checkpoint — e.g. a FaceForensics++-trained model from a source
   like Hugging Face Hub (there are a few community deepfake-detection
   checkpoints; quality varies, so evaluate before trusting results).
2. Drop the `.pt`/`.pth` file into `/models`.
3. I'll write `app/services/ai_model.py` to load it and blend its score
   with the existing forensic signals — the API contract
   (`AnalysisResponse`) already has a `model_used` field ready for this.

## Folder structure

```
server/
  app/
    main.py                — FastAPI app + router registration
    config.py               — settings (paths, limits, JWT secret)
    database.py              — SQLAlchemy engine/session
    models.py                 — ORM models (User, VideoRecord, AnalysisResult)
    schemas.py                 — Pydantic request/response schemas
    routers/
      upload.py, analyze.py, history.py, stats.py
    services/
      video_processor.py     — ffprobe metadata + OpenCV frame extraction
      forensics.py             — classical forensic signal analysis
      storage.py                — file save/validate/cleanup helpers
  tests/
    test_video_pipeline.py
  uploads/    — saved video files (gitignore this in production)
  frames/     — extracted frames per video_id
  reports/    — generated PDF reports (future)
  models/     — model checkpoints (future)
  requirements.txt
  .env.example
```
