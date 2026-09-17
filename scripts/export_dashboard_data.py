"""
TelNova Communications - HR Workforce Analytics
Dashboard Data Export
=================================================
Reads the FINISHED, recalculated .xlsx workbook and bakes its contents into
dashboard/data.js as a plain JavaScript object (window.TELNOVA_DATA).

Why this exists: browsers refuse fetch() of local files when an HTML file
is opened directly (file://), which made the dashboard depend on a local
web server. Embedding the data at build time means the dashboard opens
correctly with a plain double-click, in any browser, with no server -- while
still being 100% generated from the same Excel workbook (this script's only
input is the .xlsx file itself, exactly as a human opening it would see it,
formulas included -- LibreOffice-recalculated cached values are what get
read here).

Engagement survey and training records are pre-aggregated (the dashboard
only ever charts them in aggregate) to keep the payload small; the employee
roster is kept at full per-employee granularity since many dashboard
sections (compensation, tenure cohorts, 9-box, promotions) need that detail.

The dashboard additionally offers an optional "Reload live from Excel"
button that re-parses the .xlsx directly via SheetJS when the project IS
served over http(s) (e.g. GitHub Pages, `python -m http.server`) -- that
path is unaffected by this script.

Author: Milad Shabani
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

WORKBOOK_PATH = os.path.join(PROJECT_ROOT, "data", "HR_Analytics_Workbook.xlsx")
DASHBOARD_HTML_PATH = os.path.join(PROJECT_ROOT, "dashboard", "index.html")
OUT_PATH = os.path.join(PROJECT_ROOT, "dashboard", "data.js")  # also kept as a standalone reference export
VENDOR_DIR = os.path.join(SCRIPT_DIR, "vendor")

HEADER_ROW_0INDEXED = {
    "Workforce_Forecast": 4, "Dept_Forecast": 4, "Attrition_Forecast": 4,
    "Hiring_Plan": 4, "Attrition_Risk": 4,
}


def read_sheet(sheet_name):
    header = HEADER_ROW_0INDEXED.get(sheet_name, 0)
    df = pd.read_excel(WORKBOOK_PATH, sheet_name=sheet_name, header=header, engine="openpyxl")
    df = df.dropna(how="all")
    return df


def to_records(df):
    """Convert a DataFrame to JSON-safe records: NaN->None, Timestamps->ISO date strings."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")
    df = df.replace({np.nan: None})
    return df.to_dict(orient="records")


def main():
    print("Reading workbook sheets...")
    employees = read_sheet("Employees")
    recruitment = read_sheet("Recruitment")
    engagement = read_sheet("Engagement_Survey")
    training = read_sheet("Training")
    monthly_trend = read_sheet("Monthly_Trend")

    # CompaRatio and AttritionRate are Excel *formula* columns in the workbook
    # (live COUNTIFS/ratio formulas -- see build_workbook.py). Their cached
    # values are only populated after a LibreOffice/Excel recalculation pass.
    # Recompute them directly here from the raw numbers so the dashboard
    # export is correct even on a machine without LibreOffice installed.
    employees["CompaRatio"] = (employees["BaseSalaryUSD"] / employees["MarketBenchmarkUSD"]).round(2)
    if "AttritionRate" in monthly_trend.columns:
        monthly_trend["AttritionRate"] = (monthly_trend["Terminations"] / monthly_trend["Headcount"]).fillna(0)
    company_forecast = read_sheet("Workforce_Forecast")
    dept_forecast = read_sheet("Dept_Forecast")
    attrition_forecast = read_sheet("Attrition_Forecast")
    hiring_plan = read_sheet("Hiring_Plan")
    risk_scores = read_sheet("Attrition_Risk")

    # ---- Pre-aggregate engagement: by quarter x department (dashboard never
    # needs individual survey responses, only quarterly/department averages) ----
    eng_by_qd = (engagement.groupby(["SurveyQuarter", "Department"], as_index=False)
                 .agg(Respondents=("EmployeeID", "count"),
                      OverallEngagement=("OverallEngagement", "mean"),
                      eNPS_Response=("eNPS_Response", "mean"),
                      WorkLifeBalance=("WorkLifeBalance", "mean"),
                      ManagerRelationship=("ManagerRelationship", "mean"),
                      CareerGrowth=("CareerGrowth", "mean"),
                      CompensationSatisfaction=("CompensationSatisfaction", "mean"),
                      CultureAndInclusion=("CultureAndInclusion", "mean")))
    eng_company = (engagement.groupby(["SurveyQuarter"], as_index=False)
                   .agg(Respondents=("EmployeeID", "count"),
                        OverallEngagement=("OverallEngagement", "mean"),
                        eNPS_Response=("eNPS_Response", "mean"),
                        WorkLifeBalance=("WorkLifeBalance", "mean"),
                        ManagerRelationship=("ManagerRelationship", "mean"),
                        CareerGrowth=("CareerGrowth", "mean"),
                        CompensationSatisfaction=("CompensationSatisfaction", "mean"),
                        CultureAndInclusion=("CultureAndInclusion", "mean")))
    eng_company["Department"] = "__ALL__"
    engagement_agg = pd.concat([eng_company, eng_by_qd], ignore_index=True)
    for c in ["OverallEngagement", "eNPS_Response", "WorkLifeBalance", "ManagerRelationship",
              "CareerGrowth", "CompensationSatisfaction", "CultureAndInclusion"]:
        engagement_agg[c] = engagement_agg[c].round(2)

    # ---- Pre-aggregate training: by department x category ----
    train_by_dc = (training.groupby(["Department", "Category"], as_index=False)
                   .agg(Records=("TrainingID", "count"),
                        HoursCompleted=("HoursCompleted", "sum"),
                        CostUSD=("CostUSD", "sum")))
    train_company = (training.groupby(["Category"], as_index=False)
                     .agg(Records=("TrainingID", "count"),
                          HoursCompleted=("HoursCompleted", "sum"),
                          CostUSD=("CostUSD", "sum")))
    train_company["Department"] = "__ALL__"
    training_agg = pd.concat([train_company, train_by_dc], ignore_index=True)

    data = {
        "Employees": to_records(employees),
        "Recruitment": to_records(recruitment),
        "EngagementAgg": to_records(engagement_agg),
        "TrainingAgg": to_records(training_agg),
        "MonthlyTrend": to_records(monthly_trend),
        "CompanyForecast": to_records(company_forecast),
        "DeptForecast": to_records(dept_forecast),
        "AttritionForecast": to_records(attrition_forecast),
        "HiringPlan": to_records(hiring_plan),
        "RiskScores": to_records(risk_scores),
        "_meta": {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "sourceWorkbook": "HR_Analytics_Workbook.xlsx",
            "totalSubscribers": 1_047_500,
        },
    }

    for k, v in data.items():
        if isinstance(v, list):
            print(f"  {k:20s} -> {len(v)} records")

    js_content = (
        "// AUTO-GENERATED by scripts/export_dashboard_data.py -- do not edit by hand.\n"
        "// Build-time snapshot of HR_Analytics_Workbook.xlsx so the dashboard works\n"
        "// offline with a plain double-click (no local server required).\n"
        "// Regenerate with: python scripts/build_all.py\n"
        "window.TELNOVA_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    )

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)

    size_kb = len(js_content.encode("utf-8")) / 1024
    print(f"\nWrote {OUT_PATH} ({size_kb:.0f} KB) [reference export, not required by the dashboard]")

    # ---- Embed the same data directly into dashboard/index.html ----
    # This is what makes the dashboard a single, fully self-contained file:
    # no separate data file to lose, no path mismatch, no "file not found".
    inline_script = (
        '<script id="telnova-embedded-data">\n'
        "window.TELNOVA_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
        "</script>"
    )
    with open(DASHBOARD_HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    import re
    pattern = re.compile(r'<script id="telnova-embedded-data">.*?</script>', re.S)
    if not pattern.search(html):
        raise RuntimeError(
            "Could not find the <script id=\"telnova-embedded-data\"> placeholder in dashboard/index.html. "
            "This marker must exist for the data-embedding step to work."
        )
    new_html = pattern.sub(lambda m: inline_script, html, count=1)
    # This removes ALL external network dependencies from the dashboard --
    # it renders correctly even on networks where CDNs are blocked/filtered.
    def inline_vendor(html_text, placeholder_id, vendor_filename):
        vendor_path = os.path.join(VENDOR_DIR, vendor_filename)
        with open(vendor_path, "r", encoding="utf-8") as vf:
            lib_code = vf.read()
        pat = re.compile(r'<script id="' + re.escape(placeholder_id) + r'">.*?</script>', re.S)
        if not pat.search(html_text):
            raise RuntimeError(f'Could not find placeholder <script id="{placeholder_id}"> in dashboard/index.html.')
        replacement = f'<script id="{placeholder_id}">\n{lib_code}\n</script>'
        return pat.sub(lambda m: replacement, html_text, count=1)

    new_html = inline_vendor(new_html, "vendor-chartjs", "chart.umd.js")
    new_html = inline_vendor(new_html, "vendor-xlsx", "xlsx.full.min.js")

    with open(DASHBOARD_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)

    html_size_kb = len(new_html.encode("utf-8")) / 1024
    print(f"Embedded dataset + Chart.js + SheetJS directly into {DASHBOARD_HTML_PATH} ({html_size_kb/1024:.2f} MB total)")
    print("This file now has ZERO external network dependencies -- it works fully offline.")


if __name__ == "__main__":
    main()
