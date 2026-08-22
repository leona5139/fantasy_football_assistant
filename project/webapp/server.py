from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from project.webapp.api.draft import router as draft_router

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Fantasy Draft Assistant")


@app.get("/health")
def health():
    return {"status": "ok"}


# Router must be included before the static mount -- StaticFiles' catch-all
# at "/" would otherwise shadow every /api/* route.
app.include_router(draft_router)
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
