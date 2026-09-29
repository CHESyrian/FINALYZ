"""
AI commentary on calculated financial ratios.

FREE-tier providers/models only (via .env):
  OpenRouter (:free models), Cerebras, Groq, Gemini free tier.
On each request the client tries every provider that has an API key
until one returns a usable result (auto failover / retry loop).
Auth, rate-limit, and region failures skip the rest of that provider.
Deterministic ratio math stays in Python — AI only explains.
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
from typing import Any

logger = logging.getLogger(__name__)


class AICommentaryError(Exception):
    """Base error for AI commentary with a safe user-facing message."""

    def __init__(self, user_message: str, *, technical: str | None = None):
        self.user_message = user_message
        self.technical = technical or user_message
        super().__init__(self.technical)


class AIConfigError(AICommentaryError):
    """Missing keys / invalid provider configuration."""


class AIRateLimitError(AICommentaryError):
    """Provider rate limit / quota exceeded."""


class AIAuthError(AICommentaryError):
    """Invalid or missing API key."""


class AITimeoutError(AICommentaryError):
    """Network timeout or connectivity failure."""


class AIResponseError(AICommentaryError):
    """Empty, blocked, or unparseable model response."""


SYSTEM_PROMPT = """You are a financial analysis assistant for managers and students.
You receive pre-calculated ratios and statuses from a deterministic engine.
NEVER invent or recalculate numeric ratios. Only interpret the provided numbers.
Be concise, practical, and neutral. This is educational commentary, not investment advice.
Respond in clear English unless the user data suggests otherwise.
Return valid JSON only, with this exact shape:
{
  "executive_summary": "4-8 sentences",
  "key_strengths": ["...", "..."],
  "key_risks": ["...", "..."],
  "recommendations": ["...", "..."],
  "questions_to_ask": ["...", "..."],
  "tone_note": "one short line on overall health",
  "ratio_notes": {
    "CR": "1-2 sentences on this ratio using its calculated value and status",
    "QR": "...",
    "GPM": "..."
  }
}
Include ratio_notes only for ratios that have a numeric value (skip n/a).
Each note must reference the actual provided value and status — do not use generic fixed phrases.
"""


def _provider() -> str:
    return (os.getenv("AI_PROVIDER") or "auto").strip().lower()


def _parse_model_list(raw: str | None) -> list[str]:
    """
    Parse a free-model list from .env.
    Accepts comma, semicolon, or newline separated ids (spaces around ids ok).
    """
    if not raw or not str(raw).strip():
        return []
    parts = re.split(r"[\n,;]+", str(raw))
    out: list[str] = []
    for p in parts:
        m = p.strip().strip('"').strip("'")
        if m and m not in out:
            out.append(m)
    return out


# Built-in defaults used only when the corresponding *_FREE_MODELS env var is empty
_DEFAULT_FREE_MODELS: dict[str, tuple[str, ...]] = {
    "openrouter": (
        "openrouter/free",
        "nvidia/nemotron-nano-9b-v2:free",
        "google/gemma-3-4b-it:free",
        "google/gemma-3-12b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-8b:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
    ),
    "cerebras": (
        "llama3.1-8b",
        "llama-3.3-70b",
        "gpt-oss-120b",
        "qwen-3-32b",
    ),
    "groq": (
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "gemma2-9b-it",
    ),
    "gemini": (
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
    ),
}

# Env var that holds the comma-separated free model list for each provider
_FREE_MODELS_ENV: dict[str, str] = {
    "openrouter": "OPENROUTER_FREE_MODELS",
    "cerebras": "CEREBRAS_FREE_MODELS",
    "groq": "GROQ_FREE_MODELS",
    "gemini": "GEMINI_FREE_MODELS",
}


def _free_models_for(provider_name: str) -> list[str]:
    """Load free model list from .env, falling back to built-in defaults."""
    env_name = _FREE_MODELS_ENV.get(provider_name)
    from_env = _parse_model_list(os.getenv(env_name) if env_name else None)
    if from_env:
        return from_env
    return list(_DEFAULT_FREE_MODELS.get(provider_name) or ())


# OpenAI-compatible provider connection settings (models come from .env)
_OPENAI_COMPAT = {
    "openrouter": {
        "key_env": "OPENROUTER_API_KEY",
        "base_env": "OPENROUTER_BASE_URL",
        "model_env": "OPENROUTER_MODEL",
        "default_base": "https://openrouter.ai/api/v1",
        "default_model": "openrouter/free",
    },
    "cerebras": {
        "key_env": "CEREBRAS_API_KEY",
        "base_env": "CEREBRAS_BASE_URL",
        "model_env": "CEREBRAS_MODEL",
        "default_base": "https://api.cerebras.ai/v1",
        "default_model": "llama3.1-8b",
    },
    "groq": {
        "key_env": "GROQ_API_KEY",
        "base_env": "GROQ_BASE_URL",
        "model_env": "GROQ_MODEL",
        "default_base": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.1-8b-instant",
    },
}

# Per-request timeout (seconds) — keep short so we can try many models
_REQUEST_TIMEOUT = float(os.getenv("AI_REQUEST_TIMEOUT", "35"))

# Higher ceiling so JSON commentary is not truncated mid-string
_MAX_OUTPUT_TOKENS = 4096

# Preferred try-order when multiple keys are present
_ALL_PROVIDERS: tuple[str, ...] = (
    "openrouter",
    "cerebras",
    "groq",
    "gemini",
)

_KNOWN_PROVIDERS = set(_ALL_PROVIDERS)


def _has_key(name: str) -> bool:
    if name == "gemini":
        return bool(os.getenv("GEMINI_API_KEY", "").strip())
    cfg = _OPENAI_COMPAT.get(name)
    if not cfg:
        return False
    return bool(os.getenv(cfg["key_env"], "").strip())


def _enabled() -> bool:
    """True if at least one provider has an API key."""
    return any(_has_key(n) for n in _ALL_PROVIDERS)


def is_ai_configured() -> bool:
    return _enabled()


def _provider_order() -> list[str]:
    """
    Providers to try, in order, until one succeeds.

    - AI_PROVIDER=auto (default): every provider that has a key, preferred order.
    - AI_PROVIDER=<name>: try that provider first if keyed, then all other keyed providers.
    - Unknown names (including removed 'aimlapi') fall back to auto with a warning.
    """
    p = _provider()
    if p not in ("auto",) and p not in _KNOWN_PROVIDERS:
        logger.warning(
            "Unknown or removed AI_PROVIDER=%r — falling back to auto. "
            "Valid: auto, openrouter, cerebras, groq, gemini.",
            p,
        )
        p = "auto"

    keyed = [n for n in _ALL_PROVIDERS if _has_key(n)]
    if not keyed:
        return []

    if p == "auto":
        return keyed

    # Prefer the explicitly selected provider, then fall back to the rest
    ordered: list[str] = []
    if p in keyed:
        ordered.append(p)
    for n in keyed:
        if n not in ordered:
            ordered.append(n)
    return ordered


def _build_user_payload(report: dict[str, Any]) -> str:
    ratios_compact = []
    for r in report.get("ratios") or []:
        ratios_compact.append({
            "abbr": r.get("abbreviation"),
            "name": r.get("name"),
            "value": r.get("formatted"),
            "status": r.get("status"),
            "category": r.get("category"),
            "benchmark_median": r.get("benchmark_median"),
            "vs_benchmark": r.get("vs_benchmark"),
        })

    payload = {
        "company": report.get("company_name") or "Unknown",
        "period": report.get("period") or "N/A",
        "industry": report.get("industry_label") or report.get("industry") or "general",
        "engine_summary": report.get("summary") or "",
        "engine_strengths": report.get("strengths") or [],
        "engine_weaknesses": report.get("weaknesses") or [],
        "engine_recommendations": report.get("recommendations") or [],
        "ratios": ratios_compact,
    }
    return (
        "Analyze this financial ratio report. "
        "Use only these figures; do not invent numbers.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _repair_truncated_json(text: str) -> str:
    """
    Best-effort close of truncated JSON (common when max_tokens cuts mid-string).
    Closes open quotes, arrays, and objects so json.loads can succeed.
    """
    s = text.rstrip()
    if not s:
        return s

    # If we are inside an unclosed string, close it
    in_string = False
    escape = False
    for ch in s:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
    if in_string:
        s += '"'

    # Balance brackets (ignore content inside strings roughly by rescanning)
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in s:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()

    while stack:
        opener = stack.pop()
        s += "}" if opener == "{" else "]"

    return s


def _parse_json_response(text: str) -> dict[str, Any]:
    if not text or not str(text).strip():
        raise AIResponseError(
            "The AI returned an empty response. Please try again.",
            technical="empty model content",
        )

    text = str(text).strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    candidates = [text]
    match = re.search(r"\{[\s\S]*", text)
    if match:
        candidates.append(match.group(0))
        candidates.append(_repair_truncated_json(match.group(0)))

    data: dict[str, Any] | None = None
    last_exc: Exception | None = None
    for cand in candidates:
        try:
            parsed = json.loads(cand)
            if isinstance(parsed, dict):
                data = parsed
                break
        except json.JSONDecodeError as exc:
            last_exc = exc
            continue

    if data is None:
        try:
            parsed = json.loads(_repair_truncated_json(text))
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError as exc:
            last_exc = exc

    if data is None:
        raise AIResponseError(
            "The AI response could not be parsed. Please try again.",
            technical=f"JSON decode failed: {last_exc}; snippet={text[:200]!r}",
        )

    summary = data.get("executive_summary") or data.get("summary") or ""
    if not str(summary).strip():
        raise AIResponseError(
            "The AI did not return a usable summary. Please try again.",
            technical="missing executive_summary",
        )

    def _as_str_list(val: Any) -> list[str]:
        if val is None:
            return []
        if isinstance(val, str):
            return [val] if val.strip() else []
        if isinstance(val, list):
            return [str(x) for x in val if x is not None and str(x).strip()]
        return []

    raw_notes = data.get("ratio_notes") or data.get("ratio_commentary") or {}
    ratio_notes: dict[str, str] = {}
    if isinstance(raw_notes, dict):
        for k, v in raw_notes.items():
            if v is None:
                continue
            note = str(v).strip()
            if note:
                ratio_notes[str(k).strip().upper()] = note

    return {
        "executive_summary": str(summary).strip(),
        "key_strengths": _as_str_list(data.get("key_strengths")),
        "key_risks": _as_str_list(data.get("key_risks") or data.get("risks")),
        "recommendations": _as_str_list(data.get("recommendations")),
        "questions_to_ask": _as_str_list(data.get("questions_to_ask")),
        "tone_note": str(data.get("tone_note") or "").strip(),
        "ratio_notes": ratio_notes,
        "provider": "",
        "model": "",
    }


def _classify_http_error(provider: str, status: int, body: str) -> AICommentaryError:
    body_l = (body or "").lower()
    snippet = (body or "")[:240]

    if status in (401, 403):
        key_hints = {
            "openrouter": "OPENROUTER_API_KEY (create at openrouter.ai/keys; use :free models)",
            "groq": "GROQ_API_KEY (create at console.groq.com; try llama-3.1-8b-instant)",
            "cerebras": "CEREBRAS_API_KEY (create at cloud.cerebras.ai)",
            "gemini": "GEMINI_API_KEY (create at aistudio.google.com/apikey)",
        }
        hint = key_hints.get(provider, f"{provider.upper()}_API_KEY in .env")
        return AIAuthError(
            f"{provider.title()} rejected the API key or model access (HTTP {status}). "
            f"Refresh {hint}.",
            technical=f"{provider} HTTP {status}: {snippet}",
        )
    if status == 402:
        return AIRateLimitError(
            f"{provider.title()} requires payment or free quota is exhausted (HTTP 402). "
            "Try another provider or wait for the quota to reset.",
            technical=f"{provider} HTTP {status}: {snippet}",
        )
    if status == 404:
        return AIConfigError(
            f"{provider.title()} model was not found (HTTP 404). "
            f"Update the model id in .env to a current free model.",
            technical=f"{provider} HTTP {status}: {snippet}",
        )
    if status == 503:
        return AITimeoutError(
            f"{provider.title()} is temporarily unavailable (high demand). "
            "Will try another provider.",
            technical=f"{provider} HTTP {status}: {snippet}",
        )
    if status == 400 and ("location" in body_l or "failed_precondition" in body_l):
        return AIConfigError(
            f"{provider.title()} is not available in your region. "
            "Use OpenRouter or Cerebras instead (set AI_PROVIDER=openrouter).",
            technical=f"{provider} HTTP {status}: {snippet}",
        )
    if status == 429 or "rate limit" in body_l or "quota" in body_l or "resource_exhausted" in body_l:
        return AIRateLimitError(
            f"{provider.title()} rate limit or quota exceeded. Wait a minute and try again, "
            "or switch AI_PROVIDER in .env.",
            technical=f"{provider} HTTP {status}: {snippet}",
        )
    if status in (500, 502, 503, 504):
        return AICommentaryError(
            f"{provider.title()} is temporarily unavailable (server error). Please try again shortly.",
            technical=f"{provider} HTTP {status}: {snippet}",
        )
    if status == 404:
        return AIConfigError(
            f"{provider.title()} model was not found. Check {provider.upper()}_MODEL in .env.",
            technical=f"{provider} HTTP {status}: {snippet}",
        )
    return AICommentaryError(
        f"{provider.title()} request failed (HTTP {status}). Please try again.",
        technical=f"{provider} HTTP {status}: {snippet}",
    )


def _models_for_provider(provider_name: str) -> list[str]:
    """
    Build try-order for a provider:
      1) Preferred single model from *_MODEL env (if allowed)
      2) Full free list from *_FREE_MODELS env (or built-in defaults)
    """
    fallbacks = _free_models_for(provider_name)

    if provider_name == "gemini":
        preferred = (os.getenv("GEMINI_MODEL") or (fallbacks[0] if fallbacks else "gemini-2.0-flash")).strip()
        if preferred.startswith("models/"):
            preferred = preferred[len("models/") :]
        ordered: list[str] = []
        for m in [preferred, *fallbacks]:
            if m and m not in ordered:
                ordered.append(m)
        return ordered

    cfg = _OPENAI_COMPAT.get(provider_name)
    if not cfg:
        return fallbacks

    preferred = (os.getenv(cfg["model_env"]) or cfg["default_model"]).strip()
    if provider_name == "openrouter":
        free_ok = (
            preferred.endswith(":free")
            or preferred in ("openrouter/free", "openrouter/auto", "stealth/ox-alpha")
            or preferred in fallbacks
        )
        if not free_ok:
            logger.warning(
                "OpenRouter model %r is not free; using OPENROUTER_FREE_MODELS instead.",
                preferred,
            )
            preferred = fallbacks[0] if fallbacks else cfg["default_model"]

    ordered = []
    for m in [preferred, *fallbacks]:
        if m and m not in ordered:
            ordered.append(m)
    return ordered


def _call_openai_compatible(
    provider_name: str,
    user_content: str,
    *,
    model: str | None = None,
) -> tuple[str, str, str]:
    """Call any OpenAI-compatible provider (OpenRouter, Cerebras, Groq)."""
    try:
        from openai import OpenAI
        from openai import (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
        )
    except ImportError as exc:
        raise AIConfigError(
            "The OpenAI client library is not installed. Run: pip install openai",
            technical=str(exc),
        ) from exc

    cfg = _OPENAI_COMPAT.get(provider_name)
    if not cfg:
        raise AIConfigError(
            f"Unknown OpenAI-compatible provider: {provider_name}",
            technical=provider_name,
        )

    api_key = os.getenv(cfg["key_env"], "").strip()
    if not api_key:
        raise AIConfigError(
            f"{cfg['key_env']} is not set in .env.",
            technical=f"missing {cfg['key_env']}",
        )

    model = (model or (os.getenv(cfg["model_env"]) or cfg["default_model"])).strip()
    base_url = (os.getenv(cfg["base_env"]) or cfg["default_base"]).strip()

    client_kwargs = {
        "api_key": api_key,
        "base_url": base_url,
        "timeout": _REQUEST_TIMEOUT,
    }
    if provider_name == "openrouter":
        client_kwargs["default_headers"] = {
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:8000"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "FINALYZ"),
        }

    client = OpenAI(**client_kwargs)
    label = provider_name

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=_MAX_OUTPUT_TOKENS,
        )
    except AuthenticationError as exc:
        raise AIAuthError(
            f"{label} rejected the API key. Check {cfg['key_env']} in .env.",
            technical=str(exc),
        ) from exc
    except RateLimitError as exc:
        raise AIRateLimitError(
            f"{label} rate limit exceeded. Wait a moment or try another AI_PROVIDER.",
            technical=str(exc),
        ) from exc
    except APITimeoutError as exc:
        raise AITimeoutError(
            f"{label}/{model} timed out after {_REQUEST_TIMEOUT:.0f}s — trying next model.",
            technical=str(exc),
        ) from exc
    except APIConnectionError as exc:
        raise AITimeoutError(
            f"Could not connect to {label}/{model}. Check your internet connection.",
            technical=str(exc),
        ) from exc
    except APIStatusError as exc:
        status = getattr(exc, "status_code", None) or 0
        body = ""
        try:
            resp_obj = getattr(exc, "response", None)
            if resp_obj is not None:
                for attr in ("text", "content"):
                    try:
                        raw = getattr(resp_obj, attr, None)
                        if callable(raw):
                            raw = raw()
                        if raw:
                            body = raw if isinstance(raw, str) else str(raw)
                            break
                    except Exception:
                        continue
                if not body:
                    try:
                        body = str(resp_obj.json())  # type: ignore[attr-defined]
                    except Exception:
                        body = str(resp_obj)
            if not body:
                body = str(exc)
        except Exception:
            body = str(exc)
        body = f"model={model} {body}"
        raise _classify_http_error(label, int(status), body) from exc
    except Exception as exc:
        raise AICommentaryError(
            f"{label} request failed: {exc}",
            technical=str(exc),
        ) from exc

    if not resp.choices:
        raise AIResponseError(
            f"{label} returned no choices. Please try again.",
            technical="empty choices",
        )

    content = resp.choices[0].message.content or ""
    return content, label, model


def _call_gemini(user_content: str, *, model: str | None = None) -> tuple[str, str, str]:
    import urllib.error
    import urllib.request

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise AIConfigError(
            "GEMINI_API_KEY is not set in .env.",
            technical="missing GEMINI_API_KEY",
        )

    model = (model or (os.getenv("GEMINI_MODEL") or "gemini-2.0-flash")).strip()
    if model.startswith("models/"):
        model = model[len("models/") :]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": _MAX_OUTPUT_TOKENS,
            "responseMimeType": "application/json",
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise _classify_http_error("gemini", int(e.code), f"model={model} {err_body}") from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            raise AITimeoutError(
                f"Gemini/{model} timed out after {_REQUEST_TIMEOUT:.0f}s — trying next model.",
                technical=str(e),
            ) from e
        raise AITimeoutError(
            f"Could not connect to Gemini/{model}. Check your internet connection.",
            technical=str(e),
        ) from e
    except TimeoutError as e:
        raise AITimeoutError(
            f"Gemini/{model} timed out after {_REQUEST_TIMEOUT:.0f}s — trying next model.",
            technical=str(e),
        ) from e
    except json.JSONDecodeError as e:
        raise AIResponseError(
            "Gemini returned an invalid response. Please try again.",
            technical=str(e),
        ) from e

    prompt_feedback = raw.get("promptFeedback") or {}
    block_reason = prompt_feedback.get("blockReason")
    if block_reason:
        raise AIResponseError(
            "Gemini blocked the request (safety filter). Try again with a different report.",
            technical=f"blockReason={block_reason}",
        )

    candidates = raw.get("candidates") or []
    if not candidates:
        raise AIResponseError(
            "Gemini returned no candidates. Please try again.",
            technical=json.dumps(raw)[:300],
        )

    finish = candidates[0].get("finishReason")
    if finish and finish not in ("STOP", "MAX_TOKENS"):
        raise AIResponseError(
            f"Gemini stopped early ({finish}). Please try again.",
            technical=f"finishReason={finish}",
        )

    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts)
    if not text:
        raise AIResponseError(
            "Gemini returned empty content. Please try again.",
            technical="empty parts",
        )
    return text, "gemini", model


def _try_providers_until_success(
    user_content: str,
    *,
    parse_json: bool = True,
) -> dict[str, Any]:
    """
    Retry loop: try each configured free-tier provider until one succeeds.

        order = _provider_order()   # e.g. [openrouter, cerebras, groq, gemini]
        for name in order:
            for model in models_for(name):
                try → return result
                auth / rate-limit / region → break to next provider
                other model errors → next model
        raise AllFailed

    Returns a dict with at least provider, model, and (if parse_json) commentary fields.
    """
    order = _provider_order()
    if not order:
        raise AIConfigError(
            "No AI API keys configured. Set one or more of: "
            "OPENROUTER_API_KEY, CEREBRAS_API_KEY, GROQ_API_KEY, GEMINI_API_KEY in .env.",
            technical="no keys",
        )

    errors: list[str] = []
    last_error: Exception | None = None

    logger.info(
        "AI retry loop: providers=%s (AI_PROVIDER=%s)",
        order,
        _provider(),
    )

    for name in order:
        models = _models_for_provider(name)
        if not models:
            continue
        provider_last: Exception | None = None
        for model_id in models:
            try:
                logger.info("AI trying provider=%s model=%s", name, model_id)
                if name == "gemini":
                    text, used, model = _call_gemini(user_content, model=model_id)
                else:
                    text, used, model = _call_openai_compatible(
                        name, user_content, model=model_id
                    )

                if parse_json:
                    result = _parse_json_response(text)
                else:
                    result = {"raw_text": text}

                result["provider"] = used
                result["model"] = model
                logger.info("AI succeeded: provider=%s model=%s", used, model)
                return result

            except AICommentaryError as exc:
                provider_last = exc
                tech = (exc.technical or "").lower()
                msg = (exc.user_message or "").lower()

                # Auth failure (401/403 / invalid key) → skip ALL remaining models
                # on this provider. Retrying the same rejected key is wasted work.
                if isinstance(exc, AIAuthError):
                    logger.warning(
                        "AI provider %s auth failed → next provider (%s)",
                        name,
                        exc.user_message,
                    )
                    errors.append(f"{name}: {exc.user_message}")
                    break

                # Rate limit / quota → skip remaining models on this provider
                if (
                    isinstance(exc, AIRateLimitError)
                    or "rate limit" in msg
                    or "429" in tech
                    or "402" in tech
                ):
                    logger.warning(
                        "AI provider %s rate-limited/quota → next provider: %s",
                        name,
                        exc.user_message,
                    )
                    errors.append(f"{name}: {exc.user_message}")
                    break

                # Region / permanent config errors (e.g. Gemini geo-block) →
                # skip rest of this provider's model list
                if isinstance(exc, AIConfigError) and (
                    "not available in your region" in msg
                    or "region" in msg
                    or "failed_precondition" in tech
                ):
                    logger.warning(
                        "AI provider %s config/region block → next provider: %s",
                        name,
                        exc.user_message,
                    )
                    errors.append(f"{name}: {exc.user_message}")
                    break

                logger.warning(
                    "AI %s/%s failed → next model (%s)",
                    name,
                    model_id,
                    exc.user_message,
                )
                continue
            except Exception as exc:
                provider_last = AICommentaryError(
                    f"{name}/{model_id} failed unexpectedly.",
                    technical=str(exc),
                )
                logger.exception("Unexpected AI failure on %s/%s", name, model_id)
                continue

        if provider_last is not None:
            last_error = provider_last
            msg = getattr(provider_last, "user_message", str(provider_last))
            # Avoid duplicate if we already recorded this provider on break
            tag = f"{name}:"
            if not any(e.startswith(tag) for e in errors):
                errors.append(f"{name}: {msg}")
        continue

    # Prefer a short, actionable summary when failures are mostly auth
    authish = sum(
        1
        for e in errors
        if "403" in e or "401" in e or "rejected the API key" in e or "Forbidden" in e
    )
    if authish and authish >= max(1, len(errors) - 1):
        detail = (
            "API keys were rejected (HTTP 401/403) for: "
            + ", ".join(e.split(":")[0] for e in errors)
            + ". Create fresh free-tier keys and paste them into .env "
            "(OpenRouter, Groq, Cerebras, or Gemini). "
            "Gemini may also be blocked in your region."
        )
    else:
        detail = " | ".join(errors) if errors else "Unknown error."

    if isinstance(last_error, AICommentaryError) and len(order) == 1:
        raise last_error
    raise AICommentaryError(
        "All AI providers failed. " + detail,
        technical=getattr(last_error, "technical", "no provider succeeded"),
    ) from last_error


def generate_ai_commentary(report: dict[str, Any]) -> dict[str, Any]:
    """
    Generate AI commentary from a stored report dict (session last_report).

    Tries every free-tier provider that has an API key until one succeeds.
    Returns structured dict. Raises AICommentaryError on total failure.
    """
    if not report:
        raise AIConfigError(
            "No analysis report available. Run an analysis first.",
            technical="empty report",
        )

    user_content = _build_user_payload(report)
    return _try_providers_until_success(user_content, parse_json=True)


WHATIF_SYSTEM_PROMPT = """You are a financial scenario analyst.
You receive a BASELINE set of calculated ratios and a WHAT-IF scenario after changing some inputs.
Compare the two. Do NOT invent ratio numbers — only use the provided values.
Explain practical implications. Educational only, not investment advice.
Return valid JSON only:
{
  "executive_summary": "4-8 sentences on what changed and why it matters",
  "key_impacts": ["...", "..."],
  "risks": ["...", "..."],
  "recommendations": ["...", "..."],
  "tone_note": "one short line on overall scenario outlook"
}
"""


def generate_whatif_commentary(
    baseline_report: dict,
    whatif_result: dict,
) -> dict:
    """AI commentary comparing baseline vs what-if scenario (same free-tier retry loop)."""
    payload = {
        "company": baseline_report.get("company_name") or "Unknown",
        "period": baseline_report.get("period") or "N/A",
        "industry": baseline_report.get("industry_label") or baseline_report.get("industry") or "general",
        "input_changes": whatif_result.get("change_log") or {},
        "ratio_comparison": whatif_result.get("comparison") or [],
    }
    user_content = (
        "Analyze this what-if financial scenario. "
        "Compare baseline vs scenario ratios. Use only provided numbers.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    global SYSTEM_PROMPT
    original = SYSTEM_PROMPT
    try:
        SYSTEM_PROMPT = WHATIF_SYSTEM_PROMPT  # type: ignore
        # Shared retry loop across free providers
        bag = _try_providers_until_success(user_content, parse_json=False)
        raw = (bag.get("raw_text") or "").strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if fence:
            raw = fence.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", raw)
            data = json.loads(m.group(0)) if m else {}
        if not isinstance(data, dict):
            data = {}
        summary = (data.get("executive_summary") or data.get("summary") or "").strip()
        if not summary:
            raise AIResponseError(
                "What-if AI returned no summary. Please try again.",
                technical="empty whatif summary",
            )
        return {
            "executive_summary": summary,
            "key_impacts": [
                str(x) for x in (data.get("key_impacts") or data.get("key_strengths") or [])
            ],
            "risks": [str(x) for x in (data.get("risks") or data.get("key_risks") or [])],
            "recommendations": [str(x) for x in (data.get("recommendations") or [])],
            "tone_note": str(data.get("tone_note") or "").strip(),
            "provider": bag.get("provider", ""),
            "model": bag.get("model", ""),
        }
    finally:
        SYSTEM_PROMPT = original
