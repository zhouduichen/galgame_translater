"""Lightweight LLM client supporting Anthropic and OpenAI-compatible APIs."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

# Provider selection: "anthropic" or "openai"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").lower()
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
MAX_TOKENS = 4096

# DeepSeek defaults
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class LLMError(Exception):
    pass


def _resolve_config() -> tuple[str, str, dict[str, str], dict[str, Any]]:
    """Return (provider, api_url, headers, request_template)."""
    provider = LLM_PROVIDER
    api_key = LLM_API_KEY
    model = LLM_MODEL

    # Auto-detect: if model name contains "deepseek", use OpenAI-compatible API
    if "deepseek" in model.lower():
        provider = "openai"
        if not api_key and DEEPSEEK_API_KEY:
            api_key = DEEPSEEK_API_KEY

    match provider:
        case "anthropic":
            if not api_key:
                raise LLMError("LLM_API_KEY not set")
            url = LLM_BASE_URL or "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            template = {"model": model, "max_tokens": MAX_TOKENS}
            return provider, url, headers, template

        case "openai":
            if not api_key:
                raise LLMError("LLM_API_KEY not set")
            url = LLM_BASE_URL or DEEPSEEK_BASE_URL
            url = url.rstrip("/") + "/chat/completions"
            headers = {
                "authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            }
            template = {"model": model, "max_tokens": MAX_TOKENS}
            return provider, url, headers, template

        case _:
            raise LLMError(f"Unknown LLM provider: {provider}")


def call_llm(system: str, prompt: str) -> str:
    """Call the LLM API and return the text content."""
    provider, url, headers, req_template = _resolve_config()

    is_anthropic = provider == "anthropic"
    if is_anthropic:
        request = {**req_template, "system": system, "messages": [{"role": "user", "content": prompt}]}
    else:
        request = {
            **req_template,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }

    with httpx.Client(timeout=180) as client:
        resp = client.post(url, headers=headers, json=request)

    if resp.status_code != 200:
        raise LLMError(f"API {resp.status_code}: {resp.text[:500]}")

    body = resp.json()
    if is_anthropic:
        content = body.get("content", [])
        if not content:
            raise LLMError("Empty response from LLM")
        return content[0].get("text", "")
    else:
        choices = body.get("choices", [])
        if not choices:
            raise LLMError("Empty response from LLM")
        return choices[0].get("message", {}).get("content", "")


def call_llm_json(system: str, prompt: str) -> dict[str, Any]:
    """Call the LLM and parse the response as JSON."""
    text = call_llm(system, prompt)
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0] if "```" in text else text
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError(f"Failed to parse LLM response as JSON: {e}\nRaw:\n{text[:500]}")
