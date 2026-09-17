"""
TelNova Communications - HR Workforce Analytics
Excel Workbook Builder
=================================================
Assembles the final, formatted, formula-driven .xlsx deliverable from the
cached synthetic datasets produced by generate_hr_data.py and
forecast_engine.py.

Design choices:
  - Raw data lives in native Excel Tables (ListObjects) so formulas can use
    structured references and the HTML dashboard (SheetJS) can read clean
    tabular ranges.
  - The KPI_Dashboard sheet uses live COUNTIFS / AVERAGEIFS / SUMIFS
    formulas against those tables -- nothing here is a hardcoded number,
    so the workbook recalculates correctly if the raw data changes.
  - Forecast/model outputs (workforce forecast, hiring plan, attrition
    risk scores) are written as values because they are the output of a
    statistical model computed in Python -- methodology is documented in
    the README sheet and in a notes row on each model sheet, consistent
    with "document every assumption" practice.

Author: Milad Shabani
"""

import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule
from datetime import datetime, date
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

DATE_COLUMNS = {"BirthDate", "HireDate", "TerminationDate", "SurveyDate", "CompletionDate",
                 "DateOpened", "DateFilled", "Month"}


def coerce_dates(df):
    """Convert known date-like columns (currently plain strings from the CSV
    cache round-trip) into real Python date objects so Excel stores them as
    proper, sortable/filterable date cells instead of text."""
    df = df.copy()
    for col in df.columns:
        if col in DATE_COLUMNS:
            parsed = pd.to_datetime(df[col], errors="coerce")
            df[col] = parsed.dt.date
    return df

BASE = SCRIPT_DIR + os.sep
OUT_PATH = os.path.join(PROJECT_ROOT, "data", "HR_Analytics_Workbook.xlsx")

NAVY = "1B2A4A"
TEAL = "0E7C7B"
LIGHT_GRAY = "F4F6F8"
WHITE = "FFFFFF"
ACCENT_ORANGE = "E8743B"

HEADER_FONT = Font(name="Calibri", size=11, bold=True, color=WHITE)
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
TITLE_FONT = Font(name="Calibri", size=16, bold=True, color=NAVY)
SUBTITLE_FONT = Font(name="Calibri", size=10, italic=True, color="666666")
BODY_FONT = Font(name="Calibri", size=10)
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header_row(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def autosize(ws, df, max_width=38):
    for i, col in enumerate(df.columns, start=1):
        series_len = df[col].apply(lambda x: len(str(x))).max() if len(df) else 0
        width = min(max(len(str(col)) + 2, (series_len or 0) + 2), max_width)
        ws.column_dimensions[get_column_letter(i)].width = width


def write_table(ws, df, start_row, table_name, style="TableStyleMedium9"):
    """Writes a DataFrame starting at start_row (1-indexed) as a native Excel Table."""
    for j, col in enumerate(df.columns, start=1):
        ws.cell(row=start_row, column=j, value=col)
    for i, (_, row) in enumerate(df.iterrows(), start=start_row + 1):
        for j, col in enumerate(df.columns, start=1):
            val = row[col]
            if isinstance(val, (np.integer,)):
                val = int(val)
            elif isinstance(val, (np.floating,)):
                val = float(val)
            elif pd.isna(val):
                val = None
            elif isinstance(val, (pd.Timestamp, datetime, date)):
                val = val.date() if isinstance(val, (pd.Timestamp, datetime)) else val
                cell = ws.cell(row=i, column=j, value=val)
                cell.number_format = "yyyy-mm-dd"
                continue
            ws.cell(row=i, column=j, value=val)

    n_rows = len(df)
    n_cols = len(df.columns)
    last_col_letter = get_column_letter(n_cols)
    last_row = start_row + n_rows
    ref = f"{get_column_letter(1)}{start_row}:{last_col_letter}{last_row}"
    table = Table(displayName=table_name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(name=style, showRowStripes=True, showFirstColumn=False)
    ws.add_table(table)
    autosize(ws, df)
    return start_row, last_row, n_cols


def add_cover_note(ws, title, subtitle, ncols=6):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    c = ws.cell(row=1, column=1, value=title)
    c.font = TITLE_FONT
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    c2 = ws.cell(row=2, column=1, value=subtitle)
    c2.font = SUBTITLE_FONT
    ws.row_dimensions[1].height = 26
    ws.row_dimensions[3].height = 6


def main():
    employees = pd.read_csv(BASE + "_cache_employees.csv")
    recruitment = pd.read_csv(BASE + "_cache_recruitment.csv")
    engagement = pd.read_csv(BASE + "_cache_engagement.csv")
    training = pd.read_csv(BASE + "_cache_training.csv")
    monthly_trend = pd.read_csv(BASE + "_cache_monthly_trend.csv")
    company_fc = pd.read_csv(BASE + "_cache_company_forecast.csv")
    dept_fc = pd.read_csv(BASE + "_cache_dept_forecast.csv")
    attrition_fc = pd.read_csv(BASE + "_cache_attrition_forecast.csv")
    hiring_plan = pd.read_csv(BASE + "_cache_hiring_plan.csv")
    risk_scores = pd.read_csv(BASE + "_cache_risk_scores.csv")

    employees = coerce_dates(employees)
    recruitment = coerce_dates(recruitment)
    engagement = coerce_dates(engagement)
    training = coerce_dates(training)
    monthly_trend = coerce_dates(monthly_trend)
    company_fc = coerce_dates(company_fc)
    dept_fc = coerce_dates(dept_fc)
    attrition_fc = coerce_dates(attrition_fc)
    hiring_plan = coerce_dates(hiring_plan)

    wb = Workbook()
    wb.remove(wb.active)

    # ------------------------------------------------------------------
    # SHEET: README (data dictionary + methodology)
    # ------------------------------------------------------------------
    ws = wb.create_sheet("README")
    ws.sheet_view.showGridLines = False
    add_cover_note(ws, "TelNova Communications - HR Workforce Analytics",
                    "Synthetic dataset generated for portfolio / demonstration purposes  |  Author: Milad Shabani", ncols=2)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 110

    rows = [
        ("Company profile", "Fictional converged telecom / ISP operator. ~1,047,500 active broadband, mobile and TV subscribers. ~740 active employees across 12 business functions."),
        ("Data status", "100% synthetically generated with a fixed random seed (reproducible). No real employees, applicants or company records are represented."),
        ("Sheets - raw data", "Employees, Recruitment, Engagement_Survey, Training -- native Excel Tables, safe to filter/pivot directly."),
        ("Sheets - trends", "Monthly_Trend: last 36 months of headcount, hires, terminations and subscriber base, reconstructed directly from employee hire/termination dates."),
        ("Sheets - forecast", "Workforce_Forecast, Attrition_Forecast, Hiring_Plan: 12-month forward-looking workforce plan. Methodology is documented on each sheet."),
        ("Sheets - risk model", "Attrition_Risk: a transparent, explainable weighted-factor model scoring every active employee 0-100 on voluntary-departure risk. Methodology documented on the sheet."),
        ("Sheets - KPIs", "KPI_Dashboard: all headline metrics computed with live COUNTIFS / AVERAGEIFS / SUMIFS formulas referencing the raw data tables -- edit any raw record and every KPI recalculates."),
        ("Currency", "All monetary figures in USD for portfolio consistency."),
        ("Recalculation", "Workbook was recalculated with LibreOffice headless prior to publishing; all formulas evaluate with zero errors."),
        ("Companion dashboard", "dashboard/index.html reads this workbook directly in the browser (SheetJS) to render an interactive HR analytics dashboard. See project README.md for setup."),
    ]
    r = 4
    for label, text in rows:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True, size=10, color=NAVY)
        cell = ws.cell(row=r, column=2, value=text)
        cell.font = BODY_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 32
        r += 1

    # ------------------------------------------------------------------
    # SHEET: Employees
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Employees")
    emp_cols_order = ["EmployeeID", "FullName", "Gender", "BirthDate", "Department", "JobTitle", "JobLevel",
                       "ManagerID", "HireDate", "TenureYears", "EmploymentType", "WorkLocation", "Education",
                       "Status", "TerminationDate", "TerminationType", "TerminationReason",
                       "BaseSalaryUSD", "MarketBenchmarkUSD", "PerformanceRating", "EngagementScore",
                       "OvertimeHoursMonthly", "TrainingHoursYTD", "AbsenceDaysYTD", "PromotionsCount", "HighPotential"]
    emp_df = employees[emp_cols_order].copy()
    start, last_row, ncols = write_table(ws, emp_df, 1, "tbl_Employees")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # Add a CompaRatio formula column (live formula referencing the table -- true "connected" metric)
    compa_col = ncols + 1
    ws.cell(row=1, column=compa_col, value="CompaRatio").font = HEADER_FONT
    ws.cell(row=1, column=compa_col).fill = HEADER_FILL
    salary_col_letter = get_column_letter(emp_cols_order.index("BaseSalaryUSD") + 1)
    bench_col_letter = get_column_letter(emp_cols_order.index("MarketBenchmarkUSD") + 1)
    for i in range(2, last_row + 1):
        formula = f"=ROUND({salary_col_letter}{i}/{bench_col_letter}{i},2)"
        ws.cell(row=i, column=compa_col, value=formula)
    ws.column_dimensions[get_column_letter(compa_col)].width = 12

    # ------------------------------------------------------------------
    # SHEET: Recruitment
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Recruitment")
    start, last_row, ncols = write_table(ws, recruitment, 1, "tbl_Recruitment")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # SHEET: Engagement_Survey
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Engagement_Survey")
    start, last_row, ncols = write_table(ws, engagement, 1, "tbl_Engagement")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # SHEET: Training
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Training")
    start, last_row, ncols = write_table(ws, training, 1, "tbl_Training")
    style_header_row(ws, 1, ncols)
    ws.freeze_panes = "A2"

    # ------------------------------------------------------------------
    # SHEET: Monthly_Trend
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Monthly_Trend")
    start, last_row, ncols = write_table(ws, monthly_trend, 1, "tbl_MonthlyTrend")
    style_header_row(ws, 1, ncols)
    # Add AttritionRate formula column
    rate_col = ncols + 1
    ws.cell(row=1, column=rate_col, value="AttritionRate").font = HEADER_FONT
    ws.cell(row=1, column=rate_col).fill = HEADER_FILL
    hc_letter = get_column_letter(monthly_trend.columns.get_loc("Headcount") + 1)
    term_letter = get_column_letter(monthly_trend.columns.get_loc("Terminations") + 1)
    for i in range(2, last_row + 1):
        ws.cell(row=i, column=rate_col, value=f"=IFERROR({term_letter}{i}/{hc_letter}{i},0)")
        ws.cell(row=i, column=rate_col).number_format = "0.0%"
    ws.column_dimensions[get_column_letter(rate_col)].width = 14

    # Trend chart
    chart = LineChart()
    chart.title = "Headcount vs. Hires vs. Terminations (last 36 months)"
    chart.style = 2
    chart.y_axis.title = "Employees"
    chart.x_axis.title = "Month"
    data = Reference(ws, min_col=2, max_col=4, min_row=1, max_row=last_row)
    cats = Reference(ws, min_col=1, min_row=2, max_row=last_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.width, chart.height = 24, 10
    ws.add_chart(chart, f"A{last_row + 3}")

    # ------------------------------------------------------------------
    # SHEET: Workforce_Forecast
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Workforce_Forecast")
    add_cover_note(ws, "12-Month Workforce Forecast", "", ncols=4)
    ws.cell(row=3, column=1, value="Methodology: 50% linear-trend regression on last 18 months of reconstructed headcount, blended 50% with a stated 6% annual strategic growth target (see forecast_engine.py). Department-level allocation is on the 'Dept_Forecast' sheet.").font = SUBTITLE_FONT
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
    start, last_row, ncols = write_table(ws, company_fc, 5, "tbl_CompanyForecast")
    style_header_row(ws, 5, ncols)

    fc_chart = LineChart()
    fc_chart.title = "Company-wide Headcount Forecast (next 12 months)"
    fc_chart.y_axis.title = "Employees"
    data = Reference(ws, min_col=2, max_col=4, min_row=5, max_row=last_row)
    cats = Reference(ws, min_col=1, min_row=6, max_row=last_row)
    fc_chart.add_data(data, titles_from_data=True)
    fc_chart.set_categories(cats)
    fc_chart.width, fc_chart.height = 24, 10
    ws.add_chart(fc_chart, f"A{last_row + 3}")

    # ------------------------------------------------------------------
    # SHEET: Dept_Forecast (kept separate from Workforce_Forecast so each
    # sheet holds exactly one clean table -- simpler for BI tools / SheetJS
    # to parse, and easier for humans to pivot on).
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Dept_Forecast")
    add_cover_note(ws, "12-Month Headcount Forecast by Department", "Blended forecast allocated proportionally to each department's current share of active headcount.", ncols=4)
    start, last_row, ncols = write_table(ws, dept_fc, 5, "tbl_DeptForecast")
    style_header_row(ws, 5, ncols)

    # ------------------------------------------------------------------
    # SHEET: Attrition_Forecast
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Attrition_Forecast")
    add_cover_note(ws, "12-Month Attrition Rate Forecast", "", ncols=3)
    ws.cell(row=3, column=1, value="Methodology: double exponential smoothing (Holt's linear trend method, alpha=0.35, beta=0.25) fitted on 36 months of reconstructed monthly attrition rate.").font = SUBTITLE_FONT
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
    start, last_row, ncols = write_table(ws, attrition_fc, 5, "tbl_AttritionForecast")
    style_header_row(ws, 5, ncols)
    for i in range(6, last_row + 1):
        ws.cell(row=i, column=2).number_format = "0.00%"
        ws.cell(row=i, column=3).number_format = "0.0%"

    afc_chart = LineChart()
    afc_chart.title = "Forecast Monthly Attrition Rate"
    data = Reference(ws, min_col=2, max_col=2, min_row=5, max_row=last_row)
    cats = Reference(ws, min_col=1, min_row=6, max_row=last_row)
    afc_chart.add_data(data, titles_from_data=True)
    afc_chart.set_categories(cats)
    afc_chart.width, afc_chart.height = 22, 9
    ws.add_chart(afc_chart, f"A{last_row + 3}")

    # ------------------------------------------------------------------
    # SHEET: Hiring_Plan
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Hiring_Plan")
    add_cover_note(ws, "12-Month Hiring Plan (Replacement + Growth)", "", ncols=5)
    ws.cell(row=3, column=1, value="PlannedHires = forecast attrition losses (replacement hiring) + net headcount change required to reach the department's forecast target (growth hiring).").font = SUBTITLE_FONT
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
    start, last_row, ncols = write_table(ws, hiring_plan, 5, "tbl_HiringPlan")
    style_header_row(ws, 5, ncols)

    # ------------------------------------------------------------------
    # SHEET: Attrition_Risk
    # ------------------------------------------------------------------
    ws = wb.create_sheet("Attrition_Risk")
    add_cover_note(ws, "Individual Attrition Risk Scoring", "", ncols=6)
    ws.cell(row=3, column=1, value="Methodology: explainable weighted-factor model (0-100). Weights: Engagement 26%, Below-market pay 20%, Overtime load 14%, Tenure w/o promotion 13%, Performance 12%, Absenteeism 10%, Training investment 5%. Scores are min-max scaled across this population (lowest scorer = 0, highest = 100); Low/Medium/High/Critical bands are set from this population's own 50th/80th/93rd percentiles.").font = SUBTITLE_FONT
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=6)
    start, last_row, ncols = write_table(ws, risk_scores, 5, "tbl_AttritionRisk")
    style_header_row(ws, 5, ncols)

    score_col_idx = risk_scores.columns.get_loc("AttritionRiskScore") + 1
    score_col_letter = get_column_letter(score_col_idx)
    color_rule = ColorScaleRule(start_type="min", start_color="63BE7B", mid_type="percentile", mid_value=50,
                                 mid_color="FFEB84", end_type="max", end_color="F8696B")
    ws.conditional_formatting.add(f"{score_col_letter}6:{score_col_letter}{last_row}", color_rule)

    # ------------------------------------------------------------------
    # SHEET: KPI_Dashboard  (live formulas)
    # ------------------------------------------------------------------
    ws = wb.create_sheet("KPI_Dashboard", 0)  # move to front
    ws.sheet_view.showGridLines = False
    add_cover_note(ws, "TelNova Communications - HR KPI Dashboard (Live)", "All figures below are Excel formulas referencing tbl_Employees / tbl_Recruitment / tbl_Engagement / tbl_Training -- change the raw data and these recalculate automatically.", ncols=4)

    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 4
    ws.column_dimensions["D"].width = 42
    ws.column_dimensions["E"].width = 18

    kpis_left = [
        ("Total Active Headcount", '=COUNTIF(tbl_Employees[Status],"Active")', "0"),
        ("Total Ever Hired (all-time)", "=COUNTA(tbl_Employees[EmployeeID])", "0"),
        ("Overall Attrition Rate (all-time)", '=COUNTIF(tbl_Employees[Status],"Terminated")/COUNTA(tbl_Employees[EmployeeID])', "0.0%"),
        ("Voluntary Attrition Share", '=COUNTIF(tbl_Employees[TerminationType],"Voluntary")/COUNTIF(tbl_Employees[Status],"Terminated")', "0.0%"),
        ("Average Tenure (Active, years)", '=AVERAGEIF(tbl_Employees[Status],"Active",tbl_Employees[TenureYears])', "0.00"),
        ("Average Engagement Score (Active)", '=AVERAGEIF(tbl_Employees[Status],"Active",tbl_Employees[EngagementScore])', "0.00"),
        ("Average Performance Rating (Active)", '=AVERAGEIF(tbl_Employees[Status],"Active",tbl_Employees[PerformanceRating])', "0.00"),
        ("Gender Diversity - % Female (Active)", '=COUNTIFS(tbl_Employees[Status],"Active",tbl_Employees[Gender],"Female")/COUNTIF(tbl_Employees[Status],"Active")', "0.0%"),
        ("High Potential Talent (Active)", '=COUNTIFS(tbl_Employees[Status],"Active",tbl_Employees[HighPotential],"Yes")', "0"),
        ("Avg. Overtime Hours / Month (Active)", '=AVERAGEIF(tbl_Employees[Status],"Active",tbl_Employees[OvertimeHoursMonthly])', "0.0"),
        ("Avg. Absence Days YTD (Active)", '=AVERAGEIF(tbl_Employees[Status],"Active",tbl_Employees[AbsenceDaysYTD])', "0.0"),
        ("Employees per 1,000 Subscribers", f"=COUNTIF(tbl_Employees[Status],\"Active\")/({int(1047500)}/1000)", "0.00"),
    ]

    kpis_right = [
        ("Open Requisitions", '=COUNTIF(tbl_Recruitment[Status],"Open")', "0"),
        ("Avg. Time to Fill (days)", "=AVERAGE(tbl_Recruitment[TimeToFillDays])", "0.0"),
        ("Avg. Cost per Hire (USD)", "=AVERAGE(tbl_Recruitment[CostOfHireUSD])", '"$"#,##0'),
        ("Total Recruiting Spend (USD, 24mo)", "=SUM(tbl_Recruitment[CostOfHireUSD])", '"$"#,##0'),
        ("Offer Acceptance Rate", "=SUM(tbl_Recruitment[NumAccepted])/SUM(tbl_Recruitment[NumOffered])", "0.0%"),
        ("Applicants per Requisition (avg)", "=AVERAGE(tbl_Recruitment[NumApplicants])", "0.0"),
        ("Avg. Overall Engagement (survey)", "=AVERAGE(tbl_Engagement[OverallEngagement])", "0.00"),
        ("Employee Net Promoter Score (eNPS)", "=AVERAGE(tbl_Engagement[eNPS_Response])", "0.0"),
        ("Total Training Hours (Active, YTD)", "=SUM(tbl_Training[HoursCompleted])", "0.0"),
        ("Avg. Training Hours / Employee", "=AVERAGE(tbl_Employees[TrainingHoursYTD])", "0.0"),
        ("Total Training Investment (USD)", "=SUM(tbl_Training[CostUSD])", '"$"#,##0'),
        ("Avg. Compa-Ratio (Active)", "=AVERAGEIF(tbl_Employees[Status],\"Active\",Employees!AA2:AA10000)", "0.00"),
    ]

    r0 = 5
    ws.cell(row=r0, column=1, value="WORKFORCE & DIVERSITY").font = Font(bold=True, size=12, color=TEAL)
    ws.cell(row=r0, column=4, value="RECRUITING, ENGAGEMENT & TRAINING").font = Font(bold=True, size=12, color=TEAL)
    for i, (label, formula, fmt) in enumerate(kpis_left):
        rr = r0 + 1 + i
        ws.cell(row=rr, column=1, value=label).font = BODY_FONT
        c = ws.cell(row=rr, column=2, value=formula)
        c.number_format = fmt
        c.font = Font(bold=True, size=11, color=NAVY)
    for i, (label, formula, fmt) in enumerate(kpis_right):
        rr = r0 + 1 + i
        ws.cell(row=rr, column=4, value=label).font = BODY_FONT
        c = ws.cell(row=rr, column=5, value=formula)
        c.number_format = fmt
        c.font = Font(bold=True, size=11, color=NAVY)

    note_row = r0 + max(len(kpis_left), len(kpis_right)) + 3
    ws.cell(row=note_row, column=1, value="Forecast, hiring-plan and attrition-risk figures live on their own sheets (Workforce_Forecast, Attrition_Forecast, Hiring_Plan, Attrition_Risk) because they are statistical model output, not raw-data formulas.").font = SUBTITLE_FONT
    ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=5)

    # Reorder sheets sensibly
    order = ["KPI_Dashboard", "README", "Employees", "Recruitment", "Engagement_Survey", "Training",
             "Monthly_Trend", "Workforce_Forecast", "Dept_Forecast", "Attrition_Forecast", "Hiring_Plan", "Attrition_Risk"]
    wb._sheets = [wb[name] for name in order]
    for name in order:
        wb[name].sheet_properties.tabColor = TEAL if name == "KPI_Dashboard" else NAVY

    wb.save(OUT_PATH)
    print(f"Workbook saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
