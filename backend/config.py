"""
BlendPilot AI — Backend Application Configuration

Pydantic settings for the FastAPI server, LLM providers, Blender bridge, and storage paths.
"""

from __future__ import annotations

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BlendPilot AI Backend"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Blender Bridge
    blender_bridge_host: str = "127.0.0.1"
    blender_bridge_port: int = 9876
    blender_bridge_timeout: float = 30.0

    # LLM Settings
    groq_api_key: str = Field(default="", description="Groq API Key")
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    anthropic_api_key: str = Field(default="", description="Anthropic API Key")
    default_llm_provider: str = "groq"
    default_llm_model: str = "llama-3.3-70b-versatile"

    # Storage Paths
    output_dir: str = "output"
    checkpoints_dir: str = "output/checkpoints"


settings = Settings()
