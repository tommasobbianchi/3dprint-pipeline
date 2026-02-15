"""FastAPI entry point — CORS, routers, static file serving."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIR
from .routers import health, materials, generate

app = FastAPI(title="3dprint-pipeline Onshape Extension", version="0.1.0")

# CORS — allow Onshape iframe + local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cad.onshape.com",
        "https://nativedev.tail7d3518.ts.net",
        "http://localhost:3000",
        "http://localhost:8420",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(health.router)
app.include_router(materials.router)
app.include_router(generate.router)

# Serve frontend static files (must be last — catches all unmatched routes)
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
