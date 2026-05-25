"""
Mneme EMR - Main FastAPI Application

A minimal EMR for medical education, integrated with oread synthetic patients
and syrinx voice encounters.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.routers import patients, schedule, messages, import_, encounters, learning, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Application lifespan events."""
  import sys
  # Startup
  settings = get_settings()
  print(f"Starting Mneme EMR on {settings.host}:{settings.port}")
  print(f"Debug mode: {settings.debug}")

  # Supabase is required for all persistence (patient import, auth, learning sessions).
  # Mneme without Supabase can boot but almost every endpoint will 500. Warn loudly.
  if not (getattr(settings, "supabase_url", None) and getattr(settings, "supabase_anon_key", None)):
    print(
      "WARN: Supabase not configured (SUPABASE_URL + SUPABASE_ANON_KEY). "
      "All persistent endpoints (patients, auth, learning, import) will fail.",
      file=sys.stderr,
    )

  yield
  # Shutdown
  print("Shutting down Mneme EMR")


app = FastAPI(
  title="Mneme EMR",
  description="A minimal EMR for medical education, integrated with oread synthetic patients.",
  version="0.1.0",
  lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
  CORSMiddleware,
  allow_origins=settings.cors_origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(schedule.router)
app.include_router(messages.router)
app.include_router(import_.router)
app.include_router(encounters.router)
app.include_router(learning.router)


@app.get("/")
async def root():
  """Root endpoint."""
  return {
    "name": "Mneme EMR",
    "version": "0.1.0",
    "status": "running",
    "docs": "/docs",
  }


@app.get("/health")
async def health():
  """Health check endpoint."""
  return {"status": "healthy"}


@app.get("/api")
async def api_info():
  """API information."""
  return {
    "version": "0.1.0",
    "endpoints": {
      "auth": "/api/auth",
      "patients": "/api/patients",
      "schedule": "/api/schedule",
      "messages": "/api/messages",
      "import": "/api/import",
      "learning": "/api/learning",
    },
  }


if __name__ == "__main__":
  import uvicorn
  settings = get_settings()
  uvicorn.run(
    "src.main:app",
    host=settings.host,
    port=settings.port,
    reload=settings.debug,
  )
