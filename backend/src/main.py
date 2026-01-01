"""
Mneme EMR - Main FastAPI Application

A minimal EMR for medical education, integrated with oread synthetic patients
and syrinx voice encounters.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.routers import patients, schedule, messages, import_, encounters


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Application lifespan events."""
  # Startup
  settings = get_settings()
  print(f"Starting Mneme EMR on {settings.host}:{settings.port}")
  print(f"Debug mode: {settings.debug}")
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
app.include_router(patients.router)
app.include_router(schedule.router)
app.include_router(messages.router)
app.include_router(import_.router)
app.include_router(encounters.router)


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
      "patients": "/api/patients",
      "schedule": "/api/schedule",
      "messages": "/api/messages",
      "import": "/api/import",
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
