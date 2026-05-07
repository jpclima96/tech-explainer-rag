"""Thin helpers around the Anthropic SDK.

Centralizes prompt-cache marker construction and JSON parsing so the
extractor and verifier modules stay focused on their domain logic.
"""
from __future__ import annotations

import json
from typing import Any

import anthropic

from fact_checker.exceptions import LLMOutputError


def cached_system(prompt: str) -> list[dict[str, Any]]:
    """Build a system block list with prompt-caching enabled."""
    return [
        {
            "type": "text",
            "text": prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]


async def call_json(
    client: anthropic.AsyncAnthropic,
    *,
    model: str,
    system_prompt: str,
    user_content: str,
    max_tokens: int = 2048,
) -> Any:
    """Send a prompt-cached request and parse the JSON response.

    Raises LLMOutputError if the response is not valid JSON.
    """
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=cached_system(system_prompt),
        messages=[{"role": "user", "content": user_content}],
    )
    raw = response.content[0].text.strip()
    # Strip optional markdown fences in case the model added them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMOutputError(f"LLM returned invalid JSON: {raw[:500]!r}") from exc
