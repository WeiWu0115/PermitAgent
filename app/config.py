"""
config.py — Application configuration for PermitAgent.

Loads settings from environment variables with sensible defaults.
"""

import os

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "sk-placeholder")
GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "your-key-here")

# ---------------------------------------------------------------------------
# LLM settings
# ---------------------------------------------------------------------------
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
OPENAI_TIMEOUT_SECONDS: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "8"))
GOOGLE_MAPS_TIMEOUT_SECONDS: float = float(os.getenv("GOOGLE_MAPS_TIMEOUT_SECONDS", "5"))

# ---------------------------------------------------------------------------
# Server settings
# ---------------------------------------------------------------------------
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Pipeline settings
# ---------------------------------------------------------------------------
# Default jurisdiction when location cannot be resolved
DEFAULT_JURISDICTION: str = "City of Los Angeles"

# Maximum number of exposures to report per scene
MAX_EXPOSURES: int = 50

# Simulation scenarios to generate per scene
SIMULATION_SCENARIOS: int = 5
