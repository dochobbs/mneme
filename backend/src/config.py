"""Configuration management for Mneme EMR."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
  """Application settings loaded from environment variables."""

  # Supabase
  supabase_url: str
  supabase_anon_key: str
  supabase_service_key: str | None = None

  # Server
  host: str = "0.0.0.0"
  port: int = 8002
  debug: bool = False

  # CORS
  cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

  class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
  """Get cached settings instance."""
  return Settings()
