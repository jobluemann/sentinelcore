"""
SENTINEL CORE — AI Provider Router
Tries your configured providers (ai_providers table) in priority order.
If all fail — or none are configured — falls back to Claude as a
hardcoded last resort. Claude is NOT stored in ai_providers; it can't be
deleted, deprioritized, or misconfigured through the admin UI on purpose.

Usage:
    from backend.services.ai_router import call_ai
    result = await call_ai("Summarize AAPL's outlook in 2 sentences.")
    # result = {"text": "...", "provider_used": "openai" | "claude-fallback", "model": "..."}
"""
import os
import httpx

from backend.db import get_pool

# Set this in Render's environment if you ever want to change which Claude
# model the fallback uses, without touching code.
CLAUDE_FALLBACK_MODEL = os.environ.get("CLAUDE_FALLBACK_MODEL", "claude-sonnet-4-5")
REQUEST_TIMEOUT = 20.0


async def _get_active_providers():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM ai_providers WHERE is_active = true ORDER BY priority DESC, id ASC"
        )
        return [dict(r) for r in rows]


async def _call_openai_compatible(provider: dict, prompt: str, system: str | None) -> str:
    """Works for OpenAI, Grok (xAI), OpenRouter, and any 'custom' provider that
    speaks the standard OpenAI chat-completions format."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{provider['api_base_url'].rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": provider["model_name"],
                "messages": messages,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_claude_fallback(prompt: str, system: str | None) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — cannot use Claude fallback")

    body = {
        "model": CLAUDE_FALLBACK_MODEL,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def call_ai(prompt: str, system: str | None = None) -> dict:
    """Tries each active provider in priority order. Falls back to Claude
    if all configured providers fail, or if none are configured at all."""
    providers = await _get_active_providers()
    errors = []

    for provider in providers:
        try:
            text = await _call_openai_compatible(provider, prompt, system)
            return {"text": text, "provider_used": provider["name"], "model": provider["model_name"]}
        except Exception as e:
            errors.append(f"{provider['name']}: {e}")
            print(f"[ai_router] Provider '{provider['name']}' failed, trying next: {e}")
            continue

    # Every configured provider failed (or none exist) — last resort.
    try:
        text = await _call_claude_fallback(prompt, system)
        if errors:
            print(f"[ai_router] All configured providers failed ({'; '.join(errors)}), used Claude fallback.")
        return {"text": text, "provider_used": "claude-fallback", "model": CLAUDE_FALLBACK_MODEL}
    except Exception as e:
        raise RuntimeError(
            f"All AI providers failed, including Claude fallback. "
            f"Configured provider errors: {errors}. Claude fallback error: {e}"
        )
