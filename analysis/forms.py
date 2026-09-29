"""
Forms for manual financial data input and Excel upload.
"""

from decimal import Decimal

from django import forms


class ManualInputForm(forms.Form):
    """Manual entry of financial statement figures."""

    # Meta
    company_name = forms.CharField(
        required=False,
        max_length=200,
        label="Company name",
        widget=forms.TextInput(attrs={"placeholder": "Optional"}),
    )
    period = forms.CharField(
        required=False,
        max_length=50,
        label="Period",
        widget=forms.TextInput(attrs={"placeholder": "e.g. FY 2025"}),
    )

    industry = forms.ChoiceField(
        required=False,
        choices=[
            ("general", "General / Mixed"),
            ("manufacturing", "Manufacturing"),
            ("retail", "Retail"),
            ("services", "Services"),
            ("technology", "Technology"),
        ],
        initial="general",
        label="Industry (for benchmarks)",
        help_text="Used to compare ratios against typical industry levels.",
    )

    # Income Statement
    revenue = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=20,
        decimal_places=2,
        label="Revenue (Net Sales) *",
        help_text="Required — must be greater than zero.",
        error_messages={
            "required": "Revenue is required to run the analysis.",
            "min_value": "Revenue must be greater than zero.",
            "invalid": "Enter a valid number for Revenue (e.g. 1000000).",
        },
    )
    cogs = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="COGS (Cost of Goods Sold)",
        error_messages={"invalid": "Enter a valid number for COGS."},
    )
    gross_profit = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=2,
        label="Gross Profit",
        help_text="Leave blank to auto-calculate (Revenue − COGS).",
        error_messages={"invalid": "Enter a valid number for Gross Profit."},
    )
    operating_income = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=2,
        label="Operating Income (EBIT)",
        error_messages={"invalid": "Enter a valid number for Operating Income."},
    )
    interest_expense = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Interest Expense",
        error_messages={"invalid": "Enter a valid number for Interest Expense."},
    )
    net_income = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=2,
        label="Net Income",
        error_messages={"invalid": "Enter a valid number for Net Income."},
    )

    # Balance Sheet – Assets
    current_assets = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Current Assets",
        error_messages={"invalid": "Enter a valid number for Current Assets."},
    )
    cash = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Cash",
        error_messages={"invalid": "Enter a valid number for Cash."},
    )
    cash_equivalents = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Cash Equivalents",
        error_messages={"invalid": "Enter a valid number for Cash Equivalents."},
    )
    inventory = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Inventory",
        error_messages={"invalid": "Enter a valid number for Inventory."},
    )
    prepaid_expenses = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Prepaid Expenses",
        error_messages={"invalid": "Enter a valid number for Prepaid Expenses."},
    )
    receivables = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Accounts Receivable",
        error_messages={"invalid": "Enter a valid number for Accounts Receivable."},
    )
    total_assets = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Total Assets",
        error_messages={"invalid": "Enter a valid number for Total Assets."},
    )

    # Balance Sheet – Liabilities & Equity
    current_liabilities = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Current Liabilities",
        error_messages={"invalid": "Enter a valid number for Current Liabilities."},
    )
    accounts_payable = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Accounts Payable",
        help_text="Trade payables — unlocks DPO and Cash Conversion Cycle.",
        error_messages={"invalid": "Enter a valid number for Accounts Payable."},
    )
    total_liabilities = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Total Liabilities",
        error_messages={"invalid": "Enter a valid number for Total Liabilities."},
    )
    total_debt = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Total Debt",
        help_text="Interest-bearing debt (falls back to Total Liabilities if empty).",
        error_messages={"invalid": "Enter a valid number for Total Debt."},
    )
    equity = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=2,
        label="Shareholders' Equity",
        error_messages={"invalid": "Enter a valid number for Equity."},
    )

    # Optional averages (preferred for ATO, EM, ROA, ROE, turnover ratios)
    average_total_assets = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Average Total Assets",
        help_text="(Beginning + Ending) / 2 — preferred for Asset Turnover & Equity Multiplier.",
        error_messages={"invalid": "Enter a valid number for Average Total Assets."},
    )
    average_equity = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Average Equity",
        help_text="(Beginning + Ending) / 2 — preferred for Equity Multiplier & ROE.",
        error_messages={"invalid": "Enter a valid number for Average Equity."},
    )

    # Cash Flow Statement
    operating_cash_flow = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=2,
        label="Operating Cash Flow (OCF)",
        help_text="Cash from operating activities — unlocks cash-flow ratios.",
        error_messages={"invalid": "Enter a valid number for Operating Cash Flow."},
    )
    capital_expenditures = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        max_digits=20,
        decimal_places=2,
        label="Capital Expenditures (CapEx)",
        help_text="Enter as a positive outflow. Used with OCF for Free Cash Flow.",
        error_messages={"invalid": "Enter a valid number for CapEx."},
    )
    free_cash_flow = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=2,
        label="Free Cash Flow",
        help_text="Leave blank to auto-calculate (OCF − CapEx).",
        error_messages={"invalid": "Enter a valid number for Free Cash Flow."},
    )
    investing_cash_flow = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=2,
        label="Investing Cash Flow",
        error_messages={"invalid": "Enter a valid number for Investing Cash Flow."},
    )
    financing_cash_flow = forms.DecimalField(
        required=False,
        max_digits=20,
        decimal_places=2,
        label="Financing Cash Flow",
        error_messages={"invalid": "Enter a valid number for Financing Cash Flow."},
    )

    def clean(self):
        cleaned = super().clean()
        errors: list[str] = []

        revenue = cleaned.get("revenue")
        cogs = cleaned.get("cogs")
        current_assets = cleaned.get("current_assets")
        current_liabilities = cleaned.get("current_liabilities")
        total_assets = cleaned.get("total_assets")
        total_liabilities = cleaned.get("total_liabilities")
        equity = cleaned.get("equity")

        if revenue is not None and cogs is not None and cogs > revenue:
            errors.append("COGS is greater than Revenue — please check the figures.")

        if current_assets is not None and total_assets is not None and current_assets > total_assets:
            errors.append("Current Assets cannot be greater than Total Assets.")

        if (
            current_liabilities is not None
            and total_liabilities is not None
            and current_liabilities > total_liabilities
        ):
            errors.append("Current Liabilities cannot be greater than Total Liabilities.")

        if (
            total_assets is not None
            and total_liabilities is not None
            and equity is not None
        ):
            # Soft check: Assets ≈ Liabilities + Equity (allow small rounding)
            implied = total_liabilities + equity
            if abs(total_assets - implied) > max(Decimal("1"), total_assets * Decimal("0.05")):
                errors.append(
                    "Balance sheet may not balance: Total Assets should roughly equal "
                    "Total Liabilities + Equity. Please verify the numbers."
                )

        # Encourage enough data for a useful analysis
        useful_fields = [
            cleaned.get("net_income"),
            cleaned.get("current_assets"),
            cleaned.get("current_liabilities"),
            cleaned.get("total_assets"),
            cleaned.get("equity"),
        ]
        if revenue is not None and all(v is None for v in useful_fields):
            errors.append(
                "Only Revenue was provided. Add at least Net Income or some balance-sheet "
                "figures (Current Assets, Equity, etc.) for a meaningful analysis."
            )

        if errors:
            raise forms.ValidationError(errors)

        return cleaned


class ExcelUploadForm(forms.Form):
    """Upload an Excel financial statement."""

    file = forms.FileField(
        label="Excel file (.xlsx)",
        help_text="Max 5 MB. First sheet will be used.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx,.xlsm"}),
        error_messages={
            "required": "Please select an Excel file to upload.",
            "invalid": "The uploaded file is not valid.",
        },
    )
    company_name = forms.CharField(
        required=False,
        max_length=200,
        label="Company name (optional)",
    )
    period = forms.CharField(
        required=False,
        max_length=50,
        label="Period (optional)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. FY 2025"}),
    )
    industry = forms.ChoiceField(
        required=False,
        choices=[
            ("general", "General / Mixed"),
            ("manufacturing", "Manufacturing"),
            ("retail", "Retail"),
            ("services", "Services"),
            ("technology", "Technology"),
        ],
        initial="general",
        label="Industry (for benchmarks)",
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File is too large (max 5 MB).")
        name = f.name.lower()
        if not (name.endswith(".xlsx") or name.endswith(".xlsm")):
            raise forms.ValidationError("Please upload an .xlsx or .xlsm file.")
        return f



class WhatIfForm(forms.Form):
    """Percentage changes for what-if simulation (e.g. -10 = decrease 10%)."""

    revenue = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Revenue % change",
        help_text="e.g. -10 for 10% drop",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    cogs = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="COGS % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    net_income = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Net Income % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    operating_income = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Operating Income % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    interest_expense = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Interest Expense % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    current_assets = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Current Assets % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    current_liabilities = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Current Liabilities % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    inventory = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Inventory % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    total_assets = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Total Assets % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    total_debt = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Total Debt % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    equity = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Equity % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    operating_cash_flow = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="Operating Cash Flow % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )
    capital_expenditures = forms.DecimalField(
        required=False, max_digits=8, decimal_places=2,
        label="CapEx % change",
        widget=forms.NumberInput(attrs={"placeholder": "0", "step": "0.1", "class": "form-control form-control-sm"}),
    )

    def clean(self):
        cleaned = super().clean()
        any_change = any(
            cleaned.get(f) not in (None, 0, 0.0)
            for f in (
                "revenue", "cogs", "net_income", "operating_income", "interest_expense",
                "current_assets", "current_liabilities", "inventory",
                "total_assets", "total_debt", "equity",
                "operating_cash_flow", "capital_expenditures",
            )
        )
        if not any_change:
            raise forms.ValidationError(
                "Enter at least one non-zero percentage change to run a what-if scenario."
            )
        return cleaned



class ComparePeriodsForm(forms.Form):
    """Two-period comparison: baseline (A) vs current (B)."""

    company_name = forms.CharField(
        required=False,
        max_length=200,
        label="Company name",
        widget=forms.TextInput(attrs={"placeholder": "Optional"}),
    )
    industry = forms.ChoiceField(
        required=False,
        choices=[
            ("general", "General / Mixed"),
            ("manufacturing", "Manufacturing"),
            ("retail", "Retail"),
            ("services", "Services"),
            ("technology", "Technology"),
        ],
        initial="general",
        label="Industry",
    )
    period_a = forms.CharField(
        required=False,
        max_length=50,
        label="Period A (baseline)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. FY 2024"}),
    )
    period_b = forms.CharField(
        required=False,
        max_length=50,
        label="Period B (current)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. FY 2025"}),
    )

    # Period A core fields
    revenue_a = forms.DecimalField(min_value=Decimal("0.01"), max_digits=20, decimal_places=2, label="Revenue A *")
    cogs_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="COGS A")
    net_income_a = forms.DecimalField(required=False, max_digits=20, decimal_places=2, label="Net Income A")
    operating_income_a = forms.DecimalField(required=False, max_digits=20, decimal_places=2, label="Operating Income A")
    current_assets_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Current Assets A")
    current_liabilities_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Current Liabilities A")
    total_assets_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Total Assets A")
    total_debt_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Total Debt A")
    equity_a = forms.DecimalField(required=False, max_digits=20, decimal_places=2, label="Equity A")
    interest_expense_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Interest Expense A")
    inventory_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Inventory A")
    receivables_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Accounts Receivable A")
    accounts_payable_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Accounts Payable A")
    operating_cash_flow_a = forms.DecimalField(required=False, max_digits=20, decimal_places=2, label="Operating Cash Flow A")
    capital_expenditures_a = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="CapEx A")

    # Period B core fields
    revenue_b = forms.DecimalField(min_value=Decimal("0.01"), max_digits=20, decimal_places=2, label="Revenue B *")
    cogs_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="COGS B")
    net_income_b = forms.DecimalField(required=False, max_digits=20, decimal_places=2, label="Net Income B")
    operating_income_b = forms.DecimalField(required=False, max_digits=20, decimal_places=2, label="Operating Income B")
    current_assets_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Current Assets B")
    current_liabilities_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Current Liabilities B")
    total_assets_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Total Assets B")
    total_debt_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Total Debt B")
    equity_b = forms.DecimalField(required=False, max_digits=20, decimal_places=2, label="Equity B")
    interest_expense_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Interest Expense B")
    inventory_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Inventory B")
    receivables_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Accounts Receivable B")
    accounts_payable_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="Accounts Payable B")
    operating_cash_flow_b = forms.DecimalField(required=False, max_digits=20, decimal_places=2, label="Operating Cash Flow B")
    capital_expenditures_b = forms.DecimalField(required=False, min_value=Decimal("0"), max_digits=20, decimal_places=2, label="CapEx B")
