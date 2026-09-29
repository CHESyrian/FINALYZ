"""
Industry benchmark ranges for supported ratios.

Status and interpretation are derived from calculated ratio values
compared against industry medians/thresholds — not fixed canned text.
AI commentary can further override per-ratio notes when available.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from .models import RatioResult


Direction = Literal["higher", "lower"]


@dataclass(frozen=True, slots=True)
class Benchmark:
    median: Decimal
    good_threshold: Decimal  # min if higher-is-better, max if lower-is-better
    warning_threshold: Decimal  # softer boundary before "bad"
    direction: Direction
    note: str = ""


def _b(
    median: str,
    good: str,
    warning: str,
    direction: Direction,
    note: str = "",
) -> Benchmark:
    return Benchmark(
        median=Decimal(median),
        good_threshold=Decimal(good),
        warning_threshold=Decimal(warning),
        direction=direction,
        note=note,
    )


# abbreviation → Benchmark
_GENERAL: dict[str, Benchmark] = {
    "CR"  : _b("1.50", "1.20", "1.00", "higher", "Typical healthy range ~1.2–2.0"),
    "QR"  : _b("1.00", "0.80", "0.60", "higher"),
    "CaR" : _b("0.30", "0.20", "0.10", "higher"),
    "GPM" : _b("0.35", "0.25", "0.15", "higher"),
    "OPM" : _b("0.12", "0.06", "0.02", "higher"),
    "NPM" : _b("0.08", "0.04", "0.01", "higher"),
    "ROA" : _b("0.06", "0.03", "0.01", "higher"),
    "ROE" : _b("0.12", "0.08", "0.03", "higher"),
    "DR"  : _b("0.45", "0.55", "0.70", "lower"),
    "D/E" : _b("0.80", "1.50", "2.50", "lower"),
    "ER"  : _b("0.50", "0.35", "0.20", "higher"),
    "EM"  : _b("2.00", "2.00", "3.00", "lower", "DuPont leverage factor; higher amplifies ROE and risk"),
    "ICR" : _b("4.00", "2.50", "1.50", "higher"),
    "ATO" : _b("0.80", "0.50", "0.30", "higher"),
    "RT"  : _b("8.00", "5.00", "3.00", "higher"),
    "ITR" : _b("6.00", "3.50", "2.00", "higher"),
    "DSO" : _b("45", "45", "60", "lower", "Lower days is better"),
    "DIO" : _b("60", "60", "90", "lower", "Lower days is better"),
    "DPO" : _b("35", "30", "20", "higher", "Higher days (supplier credit) is generally better"),
    "CCC" : _b("70", "60", "90", "lower", "Shorter cycle is better"),
    "ROIC": _b("0.10", "0.10", "0.05", "higher"),
    # Cash flow
    "OCFR": _b("0.40", "0.25", "0.15", "higher"),
    "CFM" : _b("0.10", "0.05", "0.02", "higher"),
    "FCFM": _b("0.05", "0.00", "-0.05", "higher"),
    "CCR" : _b("1.00", "0.80", "0.50", "higher"),
}

_MANUFACTURING: dict[str, Benchmark] = {
    **_GENERAL,
    # Profitability — typically thinner margins, solid asset use
    "GPM" : _b("0.30", "0.20", "0.12", "higher"),
    "OPM" : _b("0.10", "0.05", "0.02", "higher"),
    "NPM" : _b("0.06", "0.03", "0.01", "higher"),
    "ROA" : _b("0.06", "0.03", "0.01", "higher"),
    "ROE" : _b("0.12", "0.07", "0.03", "higher"),
    "ROIC": _b("0.09", "0.08", "0.04", "higher"),
    # Solvency — moderate leverage is common
    "D/E" : _b("0.90", "1.80", "3.00", "lower"),
    "EM"  : _b("2.20", "2.50", "3.50", "lower"),
    "ICR" : _b("3.50", "2.00", "1.25", "higher"),
    # Efficiency & working capital — inventory-heavy
    "ATO" : _b("1.00", "0.60", "0.35", "higher"),
    "ITR" : _b("5.00", "3.00", "1.50", "higher"),
    "RT"  : _b("7.00", "4.50", "3.00", "higher"),
    "DSO" : _b("50", "50", "70", "lower", "B2B manufacturing collections often 45–60 days"),
    "DIO" : _b("75", "75", "110", "lower", "Raw materials + WIP lengthen inventory days"),
    "DPO" : _b("40", "35", "25", "higher"),
    "CCC" : _b("85", "90", "120", "lower"),
    # Cash flow
    "OCFR": _b("0.35", "0.20", "0.12", "higher"),
    "CFM" : _b("0.08", "0.04", "0.015", "higher"),
    "FCFM": _b("0.04", "-0.01", "-0.06", "higher", "CapEx intensity can compress FCF"),
    "CCR" : _b("0.95", "0.75", "0.50", "higher"),
}

_RETAIL: dict[str, Benchmark] = {
    **_GENERAL,
    # Profitability — volume over margin
    "GPM" : _b("0.28", "0.18", "0.10", "higher"),
    "OPM" : _b("0.06", "0.03", "0.01", "higher"),
    "NPM" : _b("0.04", "0.02", "0.005", "higher"),
    "ROA" : _b("0.07", "0.03", "0.01", "higher"),
    "ROE" : _b("0.14", "0.08", "0.03", "higher"),
    "ROIC": _b("0.10", "0.08", "0.04", "higher"),
    # Liquidity — often tighter
    "CR"  : _b("1.30", "1.00", "0.80", "higher"),
    "QR"  : _b("0.70", "0.50", "0.35", "higher"),
    # Efficiency — high turnover, low inventory days
    "ATO" : _b("1.80", "1.00", "0.60", "higher"),
    "ITR" : _b("8.00", "4.00", "2.00", "higher"),
    "RT"  : _b("12.00", "7.00", "4.00", "higher"),
    "DSO" : _b("20", "25", "40", "lower", "Much retail is cash/card — low receivables days"),
    "DIO" : _b("45", "50", "75", "lower"),
    "DPO" : _b("35", "30", "20", "higher"),
    "CCC" : _b("30", "40", "70", "lower", "Strong retailers run a short or negative CCC"),
    "EM"  : _b("2.50", "3.00", "4.00", "lower"),
    # Cash flow — thin margins but steady conversion
    "OCFR": _b("0.30", "0.18", "0.10", "higher"),
    "CFM" : _b("0.06", "0.03", "0.01", "higher"),
    "FCFM": _b("0.03", "0.00", "-0.04", "higher"),
    "CCR" : _b("1.10", "0.85", "0.55", "higher"),
}

_SERVICES: dict[str, Benchmark] = {
    **_GENERAL,
    # Profitability — high gross, moderate asset intensity
    "GPM" : _b("0.50", "0.35", "0.20", "higher"),
    "OPM" : _b("0.15", "0.08", "0.03", "higher"),
    "NPM" : _b("0.10", "0.05", "0.02", "higher"),
    "ROA" : _b("0.08", "0.04", "0.015", "higher"),
    "ROE" : _b("0.15", "0.09", "0.04", "higher"),
    "ROIC": _b("0.12", "0.09", "0.05", "higher"),
    "CR"  : _b("1.40", "1.10", "0.85", "higher"),
    # Efficiency — less inventory; receivables matter
    "ATO" : _b("0.70", "0.40", "0.25", "higher"),
    "ITR" : _b("10.00", "5.00", "2.50", "higher"),
    "RT"  : _b("6.00", "4.00", "2.50", "higher"),
    "DSO" : _b("55", "55", "75", "lower", "Project/billable services often have longer DSO"),
    "DIO" : _b("15", "25", "45", "lower", "Little physical inventory for pure services"),
    "DPO" : _b("30", "25", "15", "higher"),
    "CCC" : _b("40", "55", "80", "lower"),
    "EM"  : _b("1.80", "2.20", "3.00", "lower"),
    # Cash flow
    "OCFR": _b("0.45", "0.28", "0.15", "higher"),
    "CFM" : _b("0.12", "0.06", "0.025", "higher"),
    "FCFM": _b("0.08", "0.02", "-0.03", "higher"),
    "CCR" : _b("1.05", "0.80", "0.55", "higher"),
}

_TECH: dict[str, Benchmark] = {
    **_GENERAL,
    # Profitability — software/tech economics
    "GPM" : _b("0.60", "0.40", "0.25", "higher"),
    "OPM" : _b("0.18", "0.08", "0.03", "higher"),
    "NPM" : _b("0.12", "0.05", "0.02", "higher"),
    "ROA" : _b("0.08", "0.04", "0.01", "higher"),
    "ROE" : _b("0.15", "0.08", "0.03", "higher"),
    "ROIC": _b("0.14", "0.10", "0.05", "higher"),
    # Efficiency — asset-light; receivables vary by model
    "ATO" : _b("0.60", "0.35", "0.20", "higher"),
    "ITR" : _b("12.00", "6.00", "3.00", "higher"),
    "RT"  : _b("6.50", "4.00", "2.50", "higher"),
    "DSO" : _b("50", "55", "75", "lower"),
    "DIO" : _b("20", "30", "50", "lower"),
    "DPO" : _b("40", "30", "20", "higher"),
    "CCC" : _b("30", "50", "80", "lower"),
    "EM"  : _b("1.60", "2.00", "2.80", "lower", "Often equity-funded; lower leverage is common"),
    "ICR" : _b("8.00", "4.00", "2.00", "higher"),
    # Cash flow — strong when mature
    "OCFR": _b("0.50", "0.30", "0.15", "higher"),
    "CFM" : _b("0.15", "0.08", "0.03", "higher"),
    "FCFM": _b("0.10", "0.03", "-0.02", "higher"),
    "CCR" : _b("1.15", "0.90", "0.60", "higher"),
}

INDUSTRY_BENCHMARKS: dict[str, dict[str, Benchmark]] = {
    "general"      : _GENERAL,
    "manufacturing": _MANUFACTURING,
    "retail"       : _RETAIL,
    "services"     : _SERVICES,
    "technology"   : _TECH,
}

INDUSTRY_CHOICES: list[tuple[str, str]] = [
    ("general", "General / Mixed"),
    ("manufacturing", "Manufacturing"),
    ("retail", "Retail"),
    ("services", "Services"),
    ("technology", "Technology"),
]


def get_benchmarks(industry: str | None) -> dict[str, Benchmark]:
    key = (industry or "general").lower()
    return INDUSTRY_BENCHMARKS.get(key, _GENERAL)


def _format_median(median: Decimal, unit: str) -> str:
    if unit == "%":
        return f"{(median * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}%"
    return str(median.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _status_from_benchmark(value: Decimal, b: Benchmark) -> str:
    if b.direction == "higher":
        if value >= b.good_threshold:
            return "good"
        if value >= b.warning_threshold:
            return "warning"
        return "bad"
    # lower is better
    if value <= b.good_threshold:
        return "good"
    if value <= b.warning_threshold:
        return "warning"
    return "bad"


def _vs_benchmark(value: Decimal, b: Benchmark) -> str:
    """above = better than median, near = around median, below = worse than median."""
    median = b.median
    band = abs(median) * Decimal("0.15") if median != 0 else Decimal("0.05")

    if b.direction == "higher":
        if value >= median + band:
            return "above"
        if value >= median - band:
            return "near"
        return "below"
    # lower is better
    if value <= median - band:
        return "above"
    if value <= median + band:
        return "near"
    return "below"


def _dynamic_interpretation(
    ratio: RatioResult,
    value: Decimal,
    b: Benchmark,
    status: str,
    vs: str,
    median_fmt: str,
) -> str:
    """Build interpretation from actual value vs industry benchmark — not fixed copy."""
    name = ratio.name
    formatted = ratio.formatted
    direction = "higher is better" if b.direction == "higher" else "lower is better"

    if vs == "above":
        vs_phrase = f"better than the industry median ({median_fmt})"
    elif vs == "near":
        vs_phrase = f"close to the industry median ({median_fmt})"
    else:
        vs_phrase = f"weaker than the industry median ({median_fmt})"

    status_phrase = {
        "good": "within a healthy range",
        "warning": "in a caution zone",
        "bad": "outside a comfortable range",
    }.get(status, "")

    note = f" {b.note}." if b.note else ""

    return (
        f"{name} is {formatted} — {vs_phrase} "
        f"and {status_phrase} for this industry ({direction}).{note}"
    )


def compare_to_benchmark(
    ratio: RatioResult,
    industry: str | None,
) -> dict[str, str | None]:
    """
    Return comparison info for a single ratio, driven by calculated value.

    Keys: median_formatted, vs_benchmark, label, status, interpretation, note
    """
    benches = get_benchmarks(industry)
    b = benches.get(ratio.abbreviation)
    if b is None or ratio.value is None:
        return {
            "median_formatted": None,
            "vs_benchmark": None,
            "label": None,
            "status": ratio.status,
            "interpretation": ratio.interpretation,
            "note": None,
        }

    value = ratio.value
    median_fmt = _format_median(b.median, ratio.unit)
    status = _status_from_benchmark(value, b)
    vs = _vs_benchmark(value, b)

    labels = {
        "above": f"Better than median ({median_fmt})",
        "near": f"Near median ({median_fmt})",
        "below": f"Below typical ({median_fmt})",
    }

    interpretation = _dynamic_interpretation(ratio, value, b, status, vs, median_fmt)

    return {
        "median_formatted": median_fmt,
        "vs_benchmark": vs,
        "label": labels[vs],
        "status": status,
        "interpretation": interpretation,
        "note": b.note or None,
    }


def enrich_ratios_with_benchmarks(
    ratios: list[RatioResult],
    industry: str | None,
) -> list[dict]:
    """
    Attach benchmark comparison to each ratio.

    Status and interpretation are recomputed from the calculated value
    against industry benchmarks (not static text).
    """
    out = []
    for r in ratios:
        cmp_ = compare_to_benchmark(r, industry)
        status = cmp_["status"] or r.status
        interpretation = cmp_["interpretation"] or r.interpretation
        out.append({
            "name": r.name,
            "abbreviation": r.abbreviation,
            "value": str(r.value) if r.value is not None else None,
            "formatted": r.formatted,
            "unit": r.unit,
            "status": status,
            "interpretation": interpretation,
            "category": r.category,
            "formula": r.formula,
            "benchmark_median": cmp_["median_formatted"],
            "vs_benchmark": cmp_["vs_benchmark"],
            "benchmark_label": cmp_["label"],
            "benchmark_note": cmp_["note"],
            "ai_note": None,  # filled later when AI returns ratio_notes
        })
    return out


def apply_ai_ratio_notes(
    ratios: list[dict],
    ratio_notes: dict | None,
) -> list[dict]:
    """
    Merge AI per-ratio notes into enriched ratio dicts.

    When AI provides a note for an abbreviation, it becomes the primary
    interpretation (calc-based text is kept as fallback).
    """
    if not ratio_notes or not isinstance(ratio_notes, dict):
        return ratios

    # Normalize keys
    notes = {str(k).strip().upper(): str(v).strip() for k, v in ratio_notes.items() if v}

    updated = []
    for r in ratios:
        item = dict(r)
        abbr = (item.get("abbreviation") or "").upper()
        note = notes.get(abbr)
        if note:
            item["ai_note"] = note
            item["interpretation"] = note
        updated.append(item)
    return updated


def build_benchmark_scorecard(
    enriched_ratios: list[dict],
    industry: str | None = None,
) -> dict:
    """
    Summarize how the company stacks up against industry benchmarks.

    Returns counts, share of scored ratios, a simple grade, and short labels
    for the strongest / weakest areas (by vs_benchmark and status).
    Only ratios with a numeric value and a benchmark status are scored.
    """
    industry_key = (industry or "general").lower()
    industry_label = dict(INDUSTRY_CHOICES).get(industry_key, industry_key.title())

    good = warning = bad = 0
    above = near = below = 0
    scored: list[dict] = []

    for r in enriched_ratios or []:
        status = (r.get("status") or "").lower()
        if status == "n/a" or r.get("value") is None:
            continue
        if status not in ("good", "warning", "bad"):
            continue
        scored.append(r)
        if status == "good":
            good += 1
        elif status == "warning":
            warning += 1
        else:
            bad += 1

        vs = (r.get("vs_benchmark") or "").lower()
        if vs == "above":
            above += 1
        elif vs == "near":
            near += 1
        elif vs == "below":
            below += 1

    total = good + warning + bad
    if total == 0:
        return {
            "available": False,
            "industry": industry_key,
            "industry_label": industry_label,
            "total": 0,
            "good": 0,
            "warning": 0,
            "bad": 0,
            "above": 0,
            "near": 0,
            "below": 0,
            "good_pct": 0.0,
            "score_pct": 0.0,
            "grade": "N/A",
            "grade_label": "Not enough data to score against industry.",
            "summary": "Add more financial figures to compare against industry benchmarks.",
            "strengths": [],
            "watchouts": [],
        }

    # Weighted score: good=1, warning=0.5, bad=0 → percent
    score_pct = round(100.0 * (good + 0.5 * warning) / total, 1)
    good_pct = round(100.0 * good / total, 1)

    if score_pct >= 80:
        grade, grade_label = "A", "Strong vs industry"
    elif score_pct >= 65:
        grade, grade_label = "B", "Solid vs industry"
    elif score_pct >= 50:
        grade, grade_label = "C", "Mixed vs industry"
    elif score_pct >= 35:
        grade, grade_label = "D", "Below typical industry levels"
    else:
        grade, grade_label = "F", "Weak vs industry — several red flags"

    # Highlight up to 3 strengths (good + above/near) and watchouts (bad or below)
    strengths: list[str] = []
    watchouts: list[str] = []
    for r in scored:
        abbr = r.get("abbreviation") or ""
        name = r.get("name") or abbr
        label = r.get("benchmark_label") or r.get("status") or ""
        line = f"{name} ({abbr}): {r.get('formatted')} — {label}"
        st = (r.get("status") or "").lower()
        vs = (r.get("vs_benchmark") or "").lower()
        if st == "good" and vs in ("above", "near") and len(strengths) < 3:
            strengths.append(line)
        if (st == "bad" or vs == "below") and len(watchouts) < 3:
            watchouts.append(line)

    summary = (
        f"Against {industry_label}: {good} good, {warning} caution, {bad} weak "
        f"out of {total} scored ratios ({good_pct}% in healthy range). "
        f"Overall grade {grade} — {grade_label}."
    )

    return {
        "available": True,
        "industry": industry_key,
        "industry_label": industry_label,
        "total": total,
        "good": good,
        "warning": warning,
        "bad": bad,
        "above": above,
        "near": near,
        "below": below,
        "good_pct": good_pct,
        "score_pct": score_pct,
        "grade": grade,
        "grade_label": grade_label,
        "summary": summary,
        "strengths": strengths,
        "watchouts": watchouts,
    }
