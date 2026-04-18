"""Anthropic client wrapper with cached shared system prompt."""

from typing import Any

from anthropic import Anthropic

from app.config import settings
from app.services.pedagogy import SYSTEM_PEDAGOGY

_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def cached_system(extra: str | None = None) -> list[dict[str, Any]]:
    """System blocks with an ephemeral cache breakpoint on the shared pedagogy.

    The shared pedagogy prefix is long enough to exceed Opus 4.7's 4096-token
    minimum cacheable prefix; repeated generation calls in a session read from
    cache at ~0.1x cost. Any byte change to SYSTEM_PEDAGOGY invalidates.
    """
    blocks: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": SYSTEM_PEDAGOGY,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    if extra:
        blocks.append({"type": "text", "text": extra})
    return blocks
