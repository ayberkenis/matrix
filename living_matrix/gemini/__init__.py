"""
Gemini Visual Intelligence Layer for Living Matrix.

This module provides an OBSERVATIONAL ONLY visual intelligence layer that:
- Consumes simulation state snapshots (read-only)
- Generates Matrix-style images hourly using Google Gemini
- Exposes the latest generated image via /state/image API

IMPORTANT:
- Gemini is completely decoupled from simulation logic
- Image generation is async and runs in background
- Never blocks the main simulation loop
- Fails gracefully if Gemini is unavailable

Required environment variables:
- GEMINI_API_KEY: Google Gemini API key

To enable/disable image generation:
- Set GEMINI_ENABLED=true/false (default: true if API key present)
"""

from .snapshot import create_state_snapshot, StateSnapshot
from .prompt_builder import build_image_prompt, build_daily_summary
from .client import GeminiClient, GeminiError
from .worker import GeminiImageWorker, GeneratedImage
from .context_store import ContextStore

__all__ = [
    'create_state_snapshot',
    'StateSnapshot',
    'build_image_prompt',
    'build_daily_summary',
    'GeminiClient',
    'GeminiError',
    'GeminiImageWorker',
    'GeneratedImage',
    'ContextStore',
]
