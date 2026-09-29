# FINALYZ

Web application for financial statement analysis.  
Upload an Excel file or enter figures manually → calculate **up to 25 key ratios** → get a structured report with **DuPont analysis**, strengths, weaknesses, recommendations, industry benchmarks, optional **AI commentary**, **what-if simulation**, and **PDF / Excel export**.

Inputs are grouped by **income statement**, **balance sheet**, and **cash flow statement**. Only Revenue is required; more fields unlock more ratios and report sections.

Built with **Django 6**, **SQLite**, and plain **HTML/CSS/JS** (Bootstrap 5).

---

## Features

- **User accounts** — register / login / logout (Django auth)
- **Demo mode** — one-click sample company analysis (includes cash-flow figures)
- **Manual input** — fields grouped by Income Statement / Balance Sheet / Cash Flow, plus optional **Average Total Assets** and **Average Equity** for textbook turnover / DuPont denominators
- **Excel upload** — `.xlsx` / `.xlsm`, automatic header detection; large row matrices staged in **cache** (not the session)
- **Column mapping** — auto-map common headers + manual adjustment, grouped by statement (including averages)
- **Up to 25 financial ratios** across 5 categories:
  - **Liquidity** (balance sheet) — Current Ratio, Quick Ratio, Cash Ratio
  - **Profitability** (income statement / mixed) — Gross Margin, Operating Margin, Net Margin, ROA, ROE, ROIC
  - **Solvency** (balance sheet) — Debt Ratio, Debt-to-Equity, Equity Ratio, Equity Multiplier (DuPont), Interest Coverage
  - **Efficiency** (mixed) — Asset Turnover, Receivables Turnover, Inventory Turnover, DSO, DIO, DPO, Cash Conversion Cycle
  - **Cash flow** (cash flow statement) — Operating Cash Flow Ratio, Cash Flow Margin, Free Cash Flow Margin, Cash Conversion Ratio
- **DuPont Analysis** — 3-factor or 5-factor ROE decomposition; **industry-aware driver notes** (same benchmark tables as the scorecard); product vs direct ROE check
- **Industry benchmarks** — sector-specific medians for all ratios (including DSO/DIO/DPO/CCC, ROIC, EM, cash-flow); dynamic status vs median
- **Benchmark scorecard** — grade (A–F), good/caution/weak counts, and top standouts / watchouts vs chosen industry
- **Analysis report** — summary, scorecard, DuPont panel, traffic-light status, strengths / weaknesses / recommendations; sections labeled by source statement
- **AI commentary** (optional) — free-tier providers only; interprets ratios, never recalculates them
- **Multi-period comparison** — side-by-side ratios; auto-derives **(A+B)/2 averages** on period B when ending balances exist; WC and CapEx fields supported
- **Arabic UI (i18n)** — language switcher EN/AR with RTL layout
- **What-if simulation** — change key figures (including OCF / CapEx), recalculate ratios, compare to baseline
- **Export** — download report as PDF or Excel (includes scorecard grade and full DuPont components / drivers)
- **SQLite only for accounts** — statements and results live in the session, not the database

---

## Tech Stack

| Layer        | Choice                                              |
|--------------|-----------------------------------------------------|
| Backend      | Django 6.0                                          |
| Database     | SQLite (user accounts only)                         |
| Frontend     | Django templates + Bootstrap 5 + vanilla JS         |
| Excel        | openpyxl                                            |
| PDF          | reportlab                                           |
| Forms        | django-crispy-forms + crispy-bootstrap5             |
| AI           | OpenAI-compatible (OpenRouter, Cerebras, Groq) + Gemini HTTP |
| Money math   | `decimal.Decimal` (no floats)                       |

---

## Project Structure

```text
financial_analyzer/
├── manage.py
├── requirements.txt
├── .env.example
├── config/                     # Project settings & root URLs
├── accounts/                   # Login / register / logout
├── analysis/                   # Core app
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── services/               # Pure Python domain layer
│   │   ├── models.py           # FinancialStatement, RatioResult, AnalysisResult
│   │   ├── ratios.py           # All ratio calculations (core + WC days + ROIC + CF)
│   │   ├── analyzer.py         # Insights & recommendations
│   │   ├── benchmarks.py       # Industry medians & status
│   │   ├── excel_parser.py     # Excel reading & header detection
│   │   ├── mapper.py           # Column mapping & normalization
│   │   ├── exports.py          # PDF & Excel builders
│   │   ├── whatif.py           # What-if simulation
│   │   ├── ai_commentary.py    # Free-tier AI interpretation
│   │   └── sample_data.py      # Demo statement
│   └── templates/analysis/
├── templates/                  # Base layout
└── static/                     # CSS / JS
```

---

## Quick Start

### 1. Clone / open the project

```bash
cd financial_analyzer
```

### 2. Create virtual environment

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment variables

```bash
cp .env.example .env
# Edit .env: SECRET_KEY, DEBUG, ALLOWED_HOSTS
# Optionally add API keys for AI commentary (see below)
```

### 5. Database & run

```bash
python manage.py migrate
python manage.py createsuperuser   # optional
python manage.py runserver
```

Open: **http://127.0.0.1:8000/**

### Production checklist

Before deploying with `DEBUG=False`:

1. Set a strong `SECRET_KEY` in `.env` (never use the insecure default).
2. Set `DEBUG=False` and a real `ALLOWED_HOSTS` list.
3. Serve over HTTPS. With `DEBUG=False`, the app enables SSL redirect, secure cookies, HSTS, and related hardening flags (override `SECURE_SSL_REDIRECT` / `SECURE_HSTS_SECONDS` via env if needed).
4. Use a production cache backend if multiple workers share Excel staging (default is local-memory).
5. Run `python manage.py check --deploy` and fix any warnings.
6. Compile translations: `python manage.py compilemessages` (requires GNU gettext).

---

## AI Commentary (optional)

AI is used **only** to interpret already-calculated ratios. Numeric results always come from the pure-Python engine.

Supported providers — **free-tier models only** (set keys in `.env`):

| Provider   | Env vars             | Default free model |
|------------|----------------------|--------------------|
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/free` (or any `*:free` id) |
| Cerebras   | `CEREBRAS_API_KEY`   | `llama3.1-8b` |
| Groq       | `GROQ_API_KEY`       | `llama-3.1-8b-instant` |
| Gemini     | `GEMINI_API_KEY`     | `gemini-2.0-flash` |

**Retry / fallback loop** (`analysis/services/ai_commentary.py` → `_try_providers_until_success`):

```python
# 1) Build provider order from keys + AI_PROVIDER
#    auto → [openrouter, cerebras, groq, gemini] (only those with keys)
#    AI_PROVIDER=groq → [groq, openrouter, cerebras, gemini] (keyed only)
order = _provider_order()

for name in order:
    models = _models_for_provider(name)   # preferred *_MODEL + *_FREE_MODELS

    for model_id in models:
        try:
            text, used, model = call(name, model_id)
            return parse(text) | {"provider": used, "model": model}

        except AIAuthError:
            # 401 / 403 — key rejected; do not burn other models on same key
            break                         # → next provider

        except AIRateLimitError:
            # 429 / 402 / quota — skip rest of this provider
            break                         # → next provider

        except AIConfigError as exc:
            # e.g. Gemini region block
            if "region" in exc.user_message.lower():
                break                     # → next provider
            continue                      # other config → next model

        except AICommentaryError:
            continue                      # model-level failure → next model

raise AICommentaryError("All AI providers failed. …")
```

**Error → action map**

| Exception / signal | Action |
|--------------------|--------|
| `AIAuthError` (HTTP 401/403) | Skip remaining models on this provider → next provider |
| `AIRateLimitError` (429 / 402 / quota) | Same |
| Gemini region / `failed_precondition` | Same |
| Other `AICommentaryError` (404, timeout, bad JSON) | Next **model** on the same provider |
| All providers exhausted | Raise with short summary (auth-focused when keys were rejected) |

**Config notes**

- `AI_PROVIDER=auto` (recommended) — OpenRouter → Cerebras → Groq → Gemini  
- `AI_PROVIDER=<name>` — that provider first, then the rest with keys  
- Unknown / removed names (e.g. old `aimlapi`) fall back to `auto` with a log warning  
- OpenRouter non-`:free` model ids are forced onto the free list  
- Without any key, ratios still work; AI stays inactive  
- See `.env.example` for the full variable list

---

## Usage

1. **Register** a new account (or log in).
2. On the home page choose:
   - **Demo** — instant sample analysis
   - **Upload Excel** — upload `.xlsx`, map columns, analyze
   - **Enter Data** — fill the manual form, analyze
3. View the **report** with ratios, industry status badges, and recommendations.
4. Optionally:
   - Request **AI commentary**
   - Run a **what-if** scenario
   - **Export** to PDF or Excel

Only **Revenue** is required. More fields → more ratios calculated.  
Cash-flow fields (especially **Operating Cash Flow** and **CapEx**) unlock the cash-flow ratio section.

---

## The Ratios

| Category       | Source              | Ratio                          | Formula                                              |
|----------------|---------------------|--------------------------------|------------------------------------------------------|
| Liquidity      | Balance sheet       | Current Ratio (CR)             | Current Assets / Current Liabilities                 |
| Liquidity      | Balance sheet       | Quick Ratio (QR)               | (CA − Inventory − Prepaid) / CL                      |
| Liquidity      | Balance sheet       | Cash Ratio (CaR)               | (Cash + Cash Equivalents) / CL                       |
| Profitability  | Income statement    | Gross Margin (GPM)             | Gross Profit / Revenue × 100                         |
| Profitability  | Income statement    | Operating Margin (OPM)         | Operating Income / Revenue × 100                     |
| Profitability  | Income statement    | Net Margin (NPM)               | Net Income / Revenue × 100                           |
| Profitability  | Mixed               | ROA                            | Net Income / Average Total Assets × 100              |
| Profitability  | Mixed               | ROE                            | Net Income / Average Equity × 100                    |
| Profitability  | Mixed               | ROIC                           | EBIT / (Total Debt + Equity − Cash & Equivalents)    |
| Solvency       | Balance sheet       | Debt Ratio (DR)                | Total Debt / Total Assets × 100                      |
| Solvency       | Balance sheet       | Debt-to-Equity (D/E)           | Total Debt / Equity                                  |
| Solvency       | Balance sheet       | Equity Ratio (ER)              | Equity / Total Assets × 100                          |
| Solvency       | Balance sheet       | Equity Multiplier (EM)         | Average Total Assets / Average Equity (DuPont)       |
| Solvency       | Mixed               | Interest Coverage (ICR)        | EBIT / Interest Expense                              |
| Efficiency     | Mixed               | Asset Turnover (ATO)           | Revenue / Average Total Assets                       |
| Efficiency     | Mixed               | Receivables Turnover (RT)      | Net Credit Sales / Average Receivables               |
| Efficiency     | Mixed               | Inventory Turnover (ITR)       | COGS / Average Inventory                             |
| Efficiency     | Mixed               | Days Sales Outstanding (DSO)   | 365 × Average Receivables / Net Credit Sales         |
| Efficiency     | Mixed               | Days Inventory Outstanding (DIO) | 365 × Average Inventory / COGS                     |
| Efficiency     | Mixed               | Days Payable Outstanding (DPO) | 365 × Average Accounts Payable / COGS                |
| Efficiency     | Mixed               | Cash Conversion Cycle (CCC)    | DSO + DIO − DPO                                      |
| Cash flow      | Cash flow statement | Operating Cash Flow Ratio (OCFR) | OCF / Current Liabilities                          |
| Cash flow      | Cash flow statement | Cash Flow Margin (CFM)         | OCF / Revenue × 100                                  |
| Cash flow      | Cash flow statement | Free Cash Flow Margin (FCFM)   | FCF / Revenue × 100                                  |
| Cash flow      | Cash flow statement | Cash Conversion Ratio (CCR)    | OCF / Net Income                                     |

If average values are not provided, the single-period figure is used.  
Free Cash Flow is auto-computed as OCF − CapEx when both are supplied.  
Accounts Payable unlocks DPO and the Cash Conversion Cycle.

---

## Design Notes

- **Domain logic is pure Python** (`analysis/services/`) — no Django dependency, easy to unit-test.
- **All money values use `Decimal`** — avoids floating-point errors.
- **Excel data lives in the session** only for the mapping step; nothing is persisted to the DB except user accounts.
- **Column aliases** cover common header variants (e.g. “Net Sales”, “PAT”, “Trade Receivables”).
- **AI never invents numbers** — it only explains the ratios the engine already computed.
- **Benchmarks** drive traffic-light status; AI can refine per-ratio notes when configured.

---

## Requirements

See `requirements.txt` (pinned versions):

- Django 6.0.4
- python-dotenv
- openpyxl
- reportlab
- django-crispy-forms
- crispy-bootstrap5
- openai (OpenAI-compatible client for Groq / OpenRouter / Cerebras)

---

## License

Private / educational use unless otherwise specified.
