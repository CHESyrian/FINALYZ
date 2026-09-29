"""
Short-lived staging for Excel upload data.

Avoids stuffing large row matrices into the session cookie/store.
Stores payload in the Django cache under a random key; only the key
(and small meta fields) live in the session.
"""

from __future__ import annotations

import secrets
from typing import Any

from django.core.cache import cache

# 30 minutes — long enough for mapping; short enough to limit memory use
_TTL_SECONDS = 30 * 60
_CACHE_PREFIX = "fa_excel_stage:"
_SESSION_KEY = "excel_stage_id"


def stage_excel_payload(
    request,
    *,
    headers: list[str],
    rows: list[list[Any]],
    sheet_name: str,
    company: str,
    period: str,
    industry: str,
    auto_map: dict[str, str],
) -> str:
    """
    Cache the heavy Excel payload and put only a stage id in the session.
    Returns the stage id.
    """
    # Drop any previous stage for this session
    clear_excel_stage(request)

    stage_id = secrets.token_urlsafe(16)
    payload = {
        "headers": headers,
        "rows": rows,
        "sheet_name": sheet_name,
        "company": company or "",
        "period": period or "",
        "industry": industry or "general",
        "auto_map": auto_map or {},
    }
    cache.set(_CACHE_PREFIX + stage_id, payload, timeout=_TTL_SECONDS)
    request.session[_SESSION_KEY] = stage_id
    # Keep small meta in session for templates that only need labels
    request.session["excel_sheet"] = sheet_name
    request.session["excel_company"] = company or ""
    request.session["excel_period"] = period or ""
    request.session["excel_industry"] = industry or "general"
    return stage_id


def load_excel_stage(request) -> dict[str, Any] | None:
    """Load staged payload or None if missing/expired."""
    stage_id = request.session.get(_SESSION_KEY)
    if not stage_id:
        return None
    payload = cache.get(_CACHE_PREFIX + stage_id)
    if not payload:
        # Expired or evicted
        request.session.pop(_SESSION_KEY, None)
        return None
    return payload


def clear_excel_stage(request) -> None:
    """Remove staged Excel data from cache and session."""
    stage_id = request.session.pop(_SESSION_KEY, None)
    if stage_id:
        cache.delete(_CACHE_PREFIX + stage_id)
    for key in (
        "excel_headers",
        "excel_rows",
        "excel_sheet",
        "excel_company",
        "excel_period",
        "excel_industry",
        "excel_auto_map",
        "excel_stage_id",
    ):
        request.session.pop(key, None)
