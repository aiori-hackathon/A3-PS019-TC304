"""
Main FastAPI Application Entry Point for DataPulse.
Serves REST API and modern cybersecurity dashboard interface.
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .config import FRONTEND_DIR, SERVER_HOST, SERVER_PORT
from .api.routes import router
from .db.app_db import init_app_database

app = FastAPI(
    title="DataPulse API",
    description="Personal-Data Discovery and Privacy Evidence Inventory System",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Mount frontend static directory if exists
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_frontend():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "DataPulse API is running. Frontend index.html not found."}

@app.on_event("startup")
def on_startup():
    """Initializes local application database on startup."""
    init_app_database()

if __name__ == "__main__":
    uvicorn.run("src.backend.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
