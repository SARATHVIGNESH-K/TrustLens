"""
TrustLens API entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000

The Vite dev server (client/vite.config.js) proxies /api/* to this server,
so the frontend can call e.g. axios.post('/api/upload', ...) without CORS
headaches during development.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import upload, analyze, history, stats, reports

# Auto-create tables on startup. Fine for SQLite/dev; use Alembic migrations
# for production schema changes.
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve extracted frame thumbnails and original video files directly.
# NOT under /api since these are plain static assets, not JSON endpoints —
# the Vite dev proxy (client/vite.config.js) forwards these paths too.
app.mount("/frames", StaticFiles(directory=str(settings.frames_dir)), name="frames")
app.mount("/media", StaticFiles(directory=str(settings.upload_dir)), name="media")

app.include_router(upload.router)
app.include_router(reports.router)
app.include_router(analyze.router)
app.include_router(history.router)
app.include_router(stats.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": settings.app_name}
