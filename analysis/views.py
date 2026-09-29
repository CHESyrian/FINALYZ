from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_http_methods, require_GET

from .forms import ManualInputForm, ExcelUploadForm, WhatIfForm, ComparePeriodsForm
from .services import (
    FinancialStatement,
    analyze,
    parse_excel,
    auto_map_headers,
    apply_mapping,
    MAPPABLE_FIELDS,
    MAPPABLE_FIELD_GROUPS,
)
from .services.comparison import compare_periods
from .services.sample_data import get_sample_statement, get_sample_form_initial
from .services.benchmarks import (
    enrich_ratios_with_benchmarks,
    apply_ai_ratio_notes,
    build_benchmark_scorecard,
    INDUSTRY_CHOICES,
)
from .services.exports import build_excel, build_pdf
from .services.whatif import statement_to_dict, statement_from_dict, run_whatif, WHATIF_FIELDS
from .services.ai_commentary import (
    generate_ai_commentary,
    is_ai_configured,
    AICommentaryError,
    generate_whatif_commentary,
)
from .services.excel_staging import (
    stage_excel_payload,
    load_excel_stage,
    clear_excel_stage,
)

INDUSTRY_LABELS = dict(INDUSTRY_CHOICES)

# Standardized user-facing error copy (keep technical detail out of the UI)
_MSG = {
    "analysis_failed": "Analysis failed. Check your figures and try again.",
    "form_errors": "Please correct the highlighted fields and try again.",
    "upload_form": "Please fix the upload form errors and try again.",
    "excel_read": "Could not read that Excel file. Use a standard .xlsx with a header row.",
    "excel_no_headers": (
        "Could not detect any column headers. "
        "Make sure the first sheet has a header row with column names."
    ),
    "excel_no_rows": (
        "No data rows found under the header. "
        "Add at least one row of numbers below the column names."
    ),
    "excel_need_upload": "Please upload an Excel file first.",
    "excel_need_revenue": (
        "Revenue is required. Map a column to “Revenue (Net Sales) *” before analyzing."
    ),
    "excel_build": "Could not build the statement from the mapped columns. Check the mapping.",
    "export_none": "No analysis available to export. Run an analysis first.",
    "ai_none": "No analysis available. Run an analysis first.",
    "compare_form": "Please correct the form errors and try again.",
    "whatif_none": "Run an analysis first before using what-if simulation.",
    "whatif_failed": "What-if simulation failed. Check the percentages and try again.",
}


def _store_report(request, result, statement, industry: str | None = None, is_demo: bool = False):
    """Persist last analysis in session for PDF/Excel export."""
    industry = industry or "general"
    ratios = enrich_ratios_with_benchmarks(result.ratios, industry)
    scorecard = build_benchmark_scorecard(ratios, industry)
    payload = {
        "company_name": statement.company_name,
        "period": statement.period,
        "industry": industry,
        "industry_label": INDUSTRY_LABELS.get(industry, industry),
        "summary": result.summary,
        "strengths": result.strengths,
        "weaknesses": result.weaknesses,
        "recommendations": result.recommendations,
        "ratios": ratios,
        "dupont": result.dupont,
        "scorecard": scorecard,
        "is_demo": is_demo,
    }
    request.session["last_report"] = payload
    request.session["last_statement"] = statement_to_dict(statement)
    request.session.pop("last_ai_commentary", None)
    request.session.pop("last_whatif", None)
    return payload


def _run_ai_after_ratios(request, payload: dict) -> dict | None:
    """
    Send calculated ratios to AI and return commentary.

    Merges AI per-ratio notes into payload["ratios"] so interpretation
    text reflects analysis output, not static copy.
    """
    if not is_ai_configured():
        return None
    try:
        commentary = generate_ai_commentary(payload)
        request.session["last_ai_commentary"] = commentary
        payload = dict(payload)
        payload["ai_commentary"] = commentary
        # Replace static interpretation with AI ratio notes when provided
        payload["ratios"] = apply_ai_ratio_notes(
            payload.get("ratios") or [],
            commentary.get("ratio_notes"),
        )
        request.session["last_report"] = payload
        return commentary
    except AICommentaryError as exc:
        messages.warning(
            request,
            f"Ratios calculated successfully, but AI commentary failed: {exc.user_message}",
        )
        return None
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Unexpected AI failure after ratio calc")
        messages.warning(
            request,
            "Ratios calculated successfully, but AI commentary failed unexpectedly. "
            "You can retry with the AI Commentary button.",
        )
        return None


def _ratios_by_category(ratios: list) -> dict:
    """Group enriched ratio dicts (or RatioResult) by category, preserving order."""
    out: dict = {}
    for r in ratios or []:
        if isinstance(r, dict):
            cat = r.get("category") or "other"
        else:
            cat = getattr(r, "category", None) or "other"
        out.setdefault(cat, []).append(r)
    return out


def _report_context(request, result, statement, industry=None, is_demo=False):
    """
    Pipeline:
      1) calculate ratios (already done by caller via analyze())
      2) store report + benchmarks (status/interpretation from calc + industry)
      3) send ratios to AI → summary / recommendations / per-ratio notes
      4) return context for the report page
    """
    payload = _store_report(request, result, statement, industry, is_demo)
    ai_text = _run_ai_after_ratios(request, payload)
    # Re-read ratios after AI may have applied ratio_notes
    ratios = payload.get("ratios") or []
    if ai_text and request.session.get("last_report"):
        ratios = request.session["last_report"].get("ratios") or ratios

    chart_payload = {
        "ratios": ratios,
        "summary": payload["summary"],
    }
    return {
        "result": result,
        "statement": statement,
        "is_demo": is_demo,
        "industry": payload["industry"],
        "industry_label": payload["industry_label"],
        "benchmark_ratios": ratios,
        "ratios_by_category": _ratios_by_category(ratios),
        "dupont": payload.get("dupont") or result.dupont,
        "scorecard": payload.get("scorecard"),
        "chart_payload": chart_payload,
        "can_export": True,
        "ai_configured": is_ai_configured(),
        "ai_commentary": ai_text,
        "ai_status": request.session.get("last_ai_status"),
        "whatif_form": WhatIfForm(),
        "whatif_result": request.session.get("last_whatif"),
    }


@login_required
def home(request):
    return render(request, "analysis/home.html")


@login_required
def demo(request):
    statement = get_sample_statement()
    industry = "manufacturing"
    result = analyze(statement, industry=industry)
    messages.info(
        request,
        "Showing demo analysis for Demo Manufacturing Co. (FY 2025). "
        "This is sample data — try Manual Input or Excel upload with your own figures.",
    )
    ctx = _report_context(request, result, statement, industry=industry, is_demo=True)
    return render(request, "analysis/report.html", ctx)


@login_required
def manual_input(request):
    load_sample = request.GET.get("sample") == "1"

    if request.method == "POST":
        form = ManualInputForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                statement = FinancialStatement(
                    revenue=data["revenue"],
                    cogs=data.get("cogs"),
                    gross_profit=data.get("gross_profit"),
                    operating_income=data.get("operating_income"),
                    interest_expense=data.get("interest_expense"),
                    net_income=data.get("net_income"),
                    current_assets=data.get("current_assets"),
                    cash=data.get("cash"),
                    cash_equivalents=data.get("cash_equivalents"),
                    inventory=data.get("inventory"),
                    prepaid_expenses=data.get("prepaid_expenses"),
                    receivables=data.get("receivables"),
                    total_assets=data.get("total_assets"),
                    current_liabilities=data.get("current_liabilities"),
                    accounts_payable=data.get("accounts_payable"),
                    total_liabilities=data.get("total_liabilities"),
                    total_debt=data.get("total_debt"),
                    equity=data.get("equity"),
                    average_total_assets=data.get("average_total_assets"),
                    average_equity=data.get("average_equity"),
                    operating_cash_flow=data.get("operating_cash_flow"),
                    capital_expenditures=data.get("capital_expenditures"),
                    free_cash_flow=data.get("free_cash_flow"),
                    investing_cash_flow=data.get("investing_cash_flow"),
                    financing_cash_flow=data.get("financing_cash_flow"),
                    company_name=data.get("company_name") or None,
                    period=data.get("period") or None,
                )
                industry = data.get("industry") or "general"
                result = analyze(statement, industry=industry)
                ctx = _report_context(request, result, statement, industry=industry)
                return render(request, "analysis/report.html", ctx)
            except Exception:
                messages.error(request, _MSG["analysis_failed"])
        else:
            if form.non_field_errors():
                for err in form.non_field_errors():
                    messages.error(request, err)
            elif form.errors:
                messages.error(request, _MSG["form_errors"])
    else:
        if load_sample:
            form = ManualInputForm(initial=get_sample_form_initial())
            messages.info(
                request,
                "Sample data loaded for Demo Manufacturing Co. Review the figures and click Analyze.",
            )
        else:
            form = ManualInputForm()

    return render(request, "analysis/manual_input.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def excel_upload(request):
    if request.method == "POST":
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                file_obj = form.cleaned_data["file"]
                file_bytes = file_obj.read()
                parsed = parse_excel(file_bytes)

                if not parsed.headers:
                    messages.error(request, _MSG["excel_no_headers"])
                    return render(request, "analysis/excel_upload.html", {"form": form})

                if not parsed.rows:
                    messages.error(request, _MSG["excel_no_rows"])
                    return render(request, "analysis/excel_upload.html", {"form": form})

                rows_serializable = [
                    [str(v) if v is not None else None for v in row]
                    for row in parsed.rows[:50]
                ]
                stage_excel_payload(
                    request,
                    headers=parsed.headers,
                    rows=rows_serializable,
                    sheet_name=parsed.sheet_name or "",
                    company=form.cleaned_data.get("company_name") or "",
                    period=form.cleaned_data.get("period") or "",
                    industry=form.cleaned_data.get("industry") or "general",
                    auto_map=auto_map_headers(parsed.headers),
                )

                messages.success(
                    request,
                    f"File loaded ({len(parsed.headers)} columns, {len(parsed.rows)} data row(s)). "
                    "Map the columns below — Revenue is required.",
                )
                return redirect("analysis:excel_mapping")
            except Exception:
                messages.error(request, _MSG["excel_read"])
        else:
            messages.error(request, _MSG["upload_form"])
    else:
        form = ExcelUploadForm()

    return render(request, "analysis/excel_upload.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def excel_mapping(request):
    staged = load_excel_stage(request)
    if not staged:
        messages.warning(request, _MSG["excel_need_upload"])
        return redirect("analysis:excel_upload")

    headers = staged["headers"]
    rows = staged["rows"]
    auto_map = staged.get("auto_map") or {}
    company = staged.get("company") or None
    period = staged.get("period") or None
    industry = staged.get("industry") or "general"
    sheet = staged.get("sheet_name") or ""

    if request.method == "POST":
        mapping: dict[str, str] = {}
        for field_key, _label in MAPPABLE_FIELDS:
            selected = request.POST.get(f"map_{field_key}", "").strip()
            if selected:
                mapping[field_key] = selected

        if "revenue" not in mapping:
            messages.error(request, _MSG["excel_need_revenue"])
        else:
            try:
                statement = apply_mapping(
                    headers=headers,
                    rows=rows,
                    mapping=mapping,
                    company_name=company or None,
                    period=period or None,
                    row_index=0,
                )
                result = analyze(statement, industry=industry)
                clear_excel_stage(request)
                ctx = _report_context(request, result, statement, industry=industry)
                return render(request, "analysis/report.html", ctx)
            except ValueError as exc:
                messages.error(request, str(exc))
            except Exception:
                messages.error(request, _MSG["excel_build"])

    preview = {}
    if rows:
        preview = {
            headers[i]: rows[0][i] if i < len(rows[0]) else None
            for i in range(len(headers))
        }

    mapping_groups = []
    for group_title, fields in MAPPABLE_FIELD_GROUPS:
        group_items = []
        for field_key, label in fields:
            selected = auto_map.get(field_key, "")
            group_items.append(
                {
                    "key": field_key,
                    "label": label,
                    "selected": selected,
                    "auto": bool(selected),
                }
            )
        mapping_groups.append({"title": group_title, "fields": group_items})

    context = {
        "headers": headers,
        "mapping_groups": mapping_groups,
        "preview": preview,
        "sheet_name": sheet,
        "company": company,
        "period": period,
        "row_count": len(rows),
    }
    return render(request, "analysis/excel_mapping.html", context)


@login_required
@require_GET
def export_excel(request):
    report = request.session.get("last_report")
    if not report:
        messages.warning(request, _MSG["export_none"])
        return redirect("analysis:home")

    content = build_excel(report)
    company = (report.get("company_name") or "analysis").replace(" ", "_")
    filename = f"{company}_ratios.xlsx"

    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_GET
def export_pdf(request):
    report = request.session.get("last_report")
    if not report:
        messages.warning(request, _MSG["export_none"])
        return redirect("analysis:home")

    content = build_pdf(report)
    company = (report.get("company_name") or "analysis").replace(" ", "_")
    filename = f"{company}_report.pdf"

    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response



@login_required
@require_http_methods(["POST"])
def ai_commentary(request):
    """Generate AI summary/recommendations from last analysis."""
    report = request.session.get("last_report")
    if not report:
        messages.warning(request, _MSG["ai_none"])
        return redirect("analysis:home")

    if not is_ai_configured():
        request.session["last_ai_status"] = {
            "ok": False,
            "message": "AI is not configured. Add at least one free-tier API key in .env.",
            "provider": None,
            "model": None,
        }
        messages.error(
            request,
            "AI is not configured. Set API keys for OpenRouter, Cerebras, Groq, or Gemini in .env",
        )
        return redirect("analysis:report_from_session")

    try:
        commentary = generate_ai_commentary(report)
        request.session["last_ai_commentary"] = commentary
        request.session["last_ai_status"] = {
            "ok": True,
            "message": "AI commentary ready.",
            "provider": commentary.get("provider"),
            "model": commentary.get("model"),
        }
        report = dict(report)
        report["ai_commentary"] = commentary
        report["ratios"] = apply_ai_ratio_notes(
            report.get("ratios") or [],
            commentary.get("ratio_notes"),
        )
        request.session["last_report"] = report
        messages.success(
            request,
            f"AI commentary via {commentary.get('provider', 'AI')} "
            f"({commentary.get('model', '')}).",
        )
    except AICommentaryError as exc:
        request.session["last_ai_status"] = {
            "ok": False,
            "message": exc.user_message,
            "provider": None,
            "model": None,
        }
        messages.error(request, exc.user_message)
    except Exception as exc:
        request.session["last_ai_status"] = {
            "ok": False,
            "message": "Unexpected AI error. Ratios below are still valid.",
            "provider": None,
            "model": None,
        }
        messages.error(
            request,
            "AI commentary failed due to an unexpected error. Please try again.",
        )
        import logging
        logging.getLogger(__name__).exception("Unexpected AI commentary failure: %s", exc)

    return redirect("analysis:report_from_session")


@login_required
@require_GET
def report_from_session(request):
    """Re-show last report from session (after AI generation)."""
    report = request.session.get("last_report")
    if not report:
        messages.warning(request, _MSG["ai_none"])
        return redirect("analysis:home")

    # Minimal statement-like object for template
    class _Stmt:
        company_name = report.get("company_name")
        period = report.get("period")

    class _Ratio:
        def __init__(self, d):
            self.name = d.get("name")
            self.abbreviation = d.get("abbreviation")
            self.value = d.get("value")
            self.formatted = d.get("formatted")
            self.unit = d.get("unit")
            self.status = d.get("status")
            self.interpretation = d.get("interpretation")
            self.category = d.get("category")
            self.formula = d.get("formula")

    class _Result:
        def __init__(self, report):
            self.summary = report.get("summary") or ""
            self.strengths = report.get("strengths") or []
            self.weaknesses = report.get("weaknesses") or []
            self.recommendations = report.get("recommendations") or []
            self.ratios = [_Ratio(r) for r in report.get("ratios") or []]

        def ratios_by_category(self):
            out = {}
            for r in self.ratios:
                out.setdefault(r.category, []).append(r)
            return out

    result = _Result(report)
    ratios = report.get("ratios") or []
    chart_payload = {
        "ratios": ratios,
        "summary": report.get("summary") or "",
    }
    return render(
        request,
        "analysis/report.html",
        {
            "result": result,
            "statement": _Stmt(),
            "is_demo": report.get("is_demo", False),
            "industry": report.get("industry"),
            "industry_label": report.get("industry_label"),
            "benchmark_ratios": ratios,
            "ratios_by_category": _ratios_by_category(ratios),
            "dupont": report.get("dupont"),
            "scorecard": report.get("scorecard"),
            "chart_payload": chart_payload,
            "can_export": True,
            "ai_configured": is_ai_configured(),
            "ai_commentary": request.session.get("last_ai_commentary") or report.get("ai_commentary"),
            "ai_status": request.session.get("last_ai_status"),
            "whatif_form": WhatIfForm(),
            "whatif_result": request.session.get("last_whatif"),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def compare_periods_view(request):
    """Multi-period ratio comparison form + results."""
    if request.method == "POST":
        form = ComparePeriodsForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            period_a = FinancialStatement(
                revenue=d["revenue_a"],
                cogs=d.get("cogs_a"),
                net_income=d.get("net_income_a"),
                operating_income=d.get("operating_income_a"),
                interest_expense=d.get("interest_expense_a"),
                current_assets=d.get("current_assets_a"),
                current_liabilities=d.get("current_liabilities_a"),
                total_assets=d.get("total_assets_a"),
                total_debt=d.get("total_debt_a"),
                equity=d.get("equity_a"),
                inventory=d.get("inventory_a"),
                receivables=d.get("receivables_a"),
                accounts_payable=d.get("accounts_payable_a"),
                operating_cash_flow=d.get("operating_cash_flow_a"),
                capital_expenditures=d.get("capital_expenditures_a"),
                company_name=d.get("company_name") or None,
                period=d.get("period_a") or "Period A",
            )
            period_b = FinancialStatement(
                revenue=d["revenue_b"],
                cogs=d.get("cogs_b"),
                net_income=d.get("net_income_b"),
                operating_income=d.get("operating_income_b"),
                interest_expense=d.get("interest_expense_b"),
                current_assets=d.get("current_assets_b"),
                current_liabilities=d.get("current_liabilities_b"),
                total_assets=d.get("total_assets_b"),
                total_debt=d.get("total_debt_b"),
                equity=d.get("equity_b"),
                inventory=d.get("inventory_b"),
                receivables=d.get("receivables_b"),
                accounts_payable=d.get("accounts_payable_b"),
                operating_cash_flow=d.get("operating_cash_flow_b"),
                capital_expenditures=d.get("capital_expenditures_b"),
                company_name=d.get("company_name") or None,
                period=d.get("period_b") or "Period B",
            )
            industry = d.get("industry") or "general"
            comparison = compare_periods(
                period_a,
                period_b,
                industry=industry,
                label_a=period_a.period,
                label_b=period_b.period,
            )
            request.session["last_comparison"] = comparison
            return render(
                request,
                "analysis/compare_result.html",
                {"comparison": comparison},
            )
        messages.error(request, _MSG["compare_form"])
    else:
        form = ComparePeriodsForm()
    return render(request, "analysis/compare.html", {"form": form})


@require_http_methods(["GET", "POST"])
def set_language(request):
    """Switch UI language (en / ar) and persist in session + cookie."""
    from django.conf import settings
    from django.utils import translation

    lang = request.POST.get("language") or request.GET.get("language") or "en"
    supported = {code for code, _ in settings.LANGUAGES}
    if lang not in supported:
        lang = "en"
    translation.activate(lang)
    request.session["django_language"] = lang
    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or request.META.get("HTTP_REFERER")
        or "/"
    )
    response = redirect(next_url)
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        lang,
        max_age=365 * 24 * 3600,
        samesite="Lax",
    )
    return response



@login_required
@require_http_methods(["POST"])
def whatif_simulate(request):
    """Run what-if simulation on last statement, then AI impact analysis."""
    report = request.session.get("last_report")
    stmt_data = request.session.get("last_statement")
    if not report or not stmt_data:
        messages.warning(request, _MSG["whatif_none"])
        return redirect("analysis:home")

    form = WhatIfForm(request.POST)
    if not form.is_valid():
        for err in form.non_field_errors():
            messages.error(request, err)
        if form.errors and not form.non_field_errors():
            messages.error(request, "Please enter at least one non-zero percentage change.")
        return redirect("analysis:report_from_session")

    try:
        base = statement_from_dict(stmt_data)
        changes = {}
        for field, _label in WHATIF_FIELDS:
            val = form.cleaned_data.get(field)
            if val is not None and val != 0:
                changes[field] = val

        industry = report.get("industry") or "general"
        result = run_whatif(base, changes, industry=industry)

        ai_part = None
        if is_ai_configured():
            try:
                ai_part = generate_whatif_commentary(report, result)
            except AICommentaryError as exc:
                messages.warning(
                    request,
                    f"Scenario calculated, but AI impact analysis failed: {exc.user_message}",
                )
            except Exception:
                import logging
                logging.getLogger(__name__).exception("what-if AI failed")
                messages.warning(
                    request,
                    "Scenario calculated, but AI impact analysis failed unexpectedly.",
                )

        payload = {
            "change_log": result["change_log"],
            "comparison": result["comparison"],
            "ai": ai_part,
        }
        request.session["last_whatif"] = payload
        messages.success(request, "What-if scenario calculated.")
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception:
        messages.error(request, _MSG["whatif_failed"])

    return redirect("analysis:report_from_session")
