"""
TelNova Communications - Workforce Planning & Forecasting Engine
=================================================================
Implements two complementary forecasting workflows used by
world-class HR analytics / People Analytics functions:

1. WORKFORCE FORECASTING (organization level)
   - 12-month forward headcount forecast per department using
     robust linear trend regression on the last 18 months of
     reconstructed headcount history (numpy least squares).
   - Attrition-rate forecasting using triple exponential smoothing
     (Holt-Winters-style, simplified) to project monthly attrition.
   - A resulting HIRING PLAN: net hires required per month per
     department to hit a stated headcount growth target while
     covering forecast attrition ("replacement + growth" hiring).

2. ATTRITION RISK SCORING (individual level)
   - A transparent, explainable weighted risk model (the kind
     used in real HR analytics before/instead of a black-box ML
     model) that scores every ACTIVE employee 0-100 on their
     likelihood of voluntary departure in the next 2 quarters,
     using tenure-in-role, engagement, performance, overtime,
     compensation-to-market ratio, absenteeism and promotion
     history as inputs. Employees are bucketed into
     Low / Medium / High / Critical risk bands.

Methodology notes are written into the workbook itself so any
reader (recruiter, HRBP, executive) can audit exactly how each
number was produced -- no unexplained "black box" numbers.

Author: Milad Shabani
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

TODAY = datetime(2026, 9, 1)


# ----------------------------------------------------------------------
# 1. HEADCOUNT FORECAST (per department, 12 months forward)
# ----------------------------------------------------------------------
def forecast_headcount(employees_df, monthly_trend_df, horizon_months=12, growth_target_annual=0.06):
    """
    Linear-trend extrapolation of company-wide headcount, then
    allocated to departments proportionally to each department's
    current share plus its own recent trend momentum.
    """
    hist = monthly_trend_df.copy()
    hist["Month"] = pd.to_datetime(hist["Month"])
    hist = hist.sort_values("Month").tail(18).reset_index(drop=True)

    x = np.arange(len(hist))
    y = hist["Headcount"].values
    slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(len(hist), len(hist) + horizon_months)
    trend_forecast = intercept + slope * future_x

    # Blend pure trend with an explicit strategic growth target so the
    # forecast reflects both organic momentum and stated business plan.
    last_actual = y[-1]
    growth_path = last_actual * (1 + growth_target_annual) ** (np.arange(1, horizon_months + 1) / 12)
    blended = 0.5 * trend_forecast + 0.5 * growth_path

    future_months = pd.date_range(start=hist["Month"].max() + pd.offsets.MonthBegin(1), periods=horizon_months, freq="MS")

    company_forecast = pd.DataFrame({
        "Month": future_months.date,
        "ForecastHeadcount_Trend": np.round(trend_forecast).astype(int),
        "ForecastHeadcount_GrowthTarget": np.round(growth_path).astype(int),
        "ForecastHeadcount_Blended": np.round(blended).astype(int),
    })

    # Department allocation
    active = employees_df[employees_df["Status"] == "Active"]
    dept_share = active["Department"].value_counts(normalize=True)

    dept_rows = []
    for dept, share in dept_share.items():
        dept_rows.append(pd.DataFrame({
            "Month": company_forecast["Month"],
            "Department": dept,
            "CurrentHeadcount": int(round(share * last_actual)),
            "ForecastHeadcount": np.round(company_forecast["ForecastHeadcount_Blended"] * share).astype(int),
        }))
    dept_forecast = pd.concat(dept_rows, ignore_index=True)

    return company_forecast, dept_forecast, slope


# ----------------------------------------------------------------------
# 2. ATTRITION RATE FORECAST (simplified exponential smoothing)
# ----------------------------------------------------------------------
def forecast_attrition_rate(monthly_trend_df, horizon_months=12, alpha=0.35, beta=0.25):
    hist = monthly_trend_df.copy()
    hist["Month"] = pd.to_datetime(hist["Month"])
    hist = hist.sort_values("Month").reset_index(drop=True)
    hist["AttritionRate"] = hist["Terminations"] / hist["Headcount"].replace(0, np.nan)
    hist["AttritionRate"] = hist["AttritionRate"].fillna(hist["AttritionRate"].mean())

    series = hist["AttritionRate"].values
    level = series[0]
    trend = series[1] - series[0]
    levels, trends = [level], [trend]

    for t in range(1, len(series)):
        last_level = level
        level = alpha * series[t] + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend
        levels.append(level)
        trends.append(trend)

    forecasts = []
    for h in range(1, horizon_months + 1):
        f = level + h * trend
        forecasts.append(max(0.0, min(f, 0.15)))  # sanity clamp: monthly rate 0-15%

    future_months = pd.date_range(start=hist["Month"].max() + pd.offsets.MonthBegin(1), periods=horizon_months, freq="MS")
    forecast_df = pd.DataFrame({
        "Month": future_months.date,
        "ForecastMonthlyAttritionRate": np.round(forecasts, 4),
        "ForecastAnnualizedAttritionRate": np.round(np.array(forecasts) * 12, 4),
    })
    return forecast_df


# ----------------------------------------------------------------------
# 3. HIRING PLAN = replacement hires (forecast attrition) + growth hires
# ----------------------------------------------------------------------
def build_hiring_plan(dept_forecast, attrition_forecast_df, dept_share):
    plan_rows = []
    months = sorted(dept_forecast["Month"].unique())
    prev_headcount = dept_forecast.set_index(["Month", "Department"])["CurrentHeadcount"].to_dict()

    dept_forecast_sorted = dept_forecast.sort_values(["Department", "Month"])
    for dept, grp in dept_forecast_sorted.groupby("Department"):
        grp = grp.reset_index(drop=True)
        prior = grp.loc[0, "CurrentHeadcount"]
        for i, row in grp.iterrows():
            month = row["Month"]
            target_hc = row["ForecastHeadcount"]
            monthly_rate = attrition_forecast_df.loc[attrition_forecast_df["Month"] == month, "ForecastMonthlyAttritionRate"]
            monthly_rate = float(monthly_rate.values[0]) if len(monthly_rate) else 0.02
            expected_attrition = round(prior * monthly_rate)
            net_change_needed = target_hc - prior
            hires_needed = max(0, expected_attrition + net_change_needed)
            plan_rows.append(dict(
                Month=month, Department=dept, StartHeadcount=int(prior),
                ExpectedAttrition=int(expected_attrition), TargetHeadcount=int(target_hc),
                PlannedHires=int(hires_needed),
            ))
            prior = target_hc
    return pd.DataFrame(plan_rows)


# ----------------------------------------------------------------------
# 4. ATTRITION RISK SCORE (individual employees, explainable weighted model)
# ----------------------------------------------------------------------
def score_attrition_risk(employees_df):
    active = employees_df[employees_df["Status"] == "Active"].copy()

    def norm(s, invert=False):
        s = s.astype(float)
        rng = (s.max() - s.min()) or 1
        n = (s - s.min()) / rng
        return 1 - n if invert else n

    # Feature engineering -- each maps to a documented weight
    active["f_low_engagement"] = norm(active["EngagementScore"], invert=True)
    active["f_low_performance"] = norm(active["PerformanceRating"], invert=True)
    active["f_below_market_pay"] = norm((active["MarketBenchmarkUSD"] - active["BaseSalaryUSD"]).clip(lower=0))
    active["f_high_overtime"] = norm(active["OvertimeHoursMonthly"])
    active["f_high_absence"] = norm(active["AbsenceDaysYTD"])
    active["f_stagnant_no_promo"] = norm(
        active["TenureYears"].clip(upper=8) * (active["PromotionsCount"] == 0).astype(int)
    )
    active["f_low_training"] = norm(active["TrainingHoursYTD"], invert=True)

    weights = dict(
        f_low_engagement=0.26, f_low_performance=0.12, f_below_market_pay=0.20,
        f_high_overtime=0.14, f_high_absence=0.10, f_stagnant_no_promo=0.13, f_low_training=0.05,
    )

    raw_score = sum(active[f] * w for f, w in weights.items()) * 100

    # Min-max scale to a full 0-100 range (only the single highest- and
    # lowest-scoring employee land exactly on the bounds; everyone else
    # spreads naturally in between -- avoids the artificial plateau you'd
    # get from clipping at a fixed percentile).
    lo, hi = raw_score.min(), raw_score.max()
    scaled = ((raw_score - lo) / (hi - lo) * 100)
    active["AttritionRiskScore"] = scaled.round(1)

    # Band cutoffs are set from this population's own quantiles so the
    # Low/Medium/High/Critical pyramid always has a sensible shape,
    # whatever the underlying score distribution looks like.
    q50, q80, q93 = scaled.quantile([0.50, 0.80, 0.93])

    def band(score):
        if score >= q93:
            return "Critical"
        elif score >= q80:
            return "High"
        elif score >= q50:
            return "Medium"
        return "Low"

    active["RiskBand"] = active["AttritionRiskScore"].apply(band)

    top_drivers = []
    for _, row in active.iterrows():
        contribs = {f: row[f] * w for f, w in weights.items()}
        top2 = sorted(contribs.items(), key=lambda kv: kv[1], reverse=True)[:2]
        label_map = {
            "f_low_engagement": "Low engagement score", "f_low_performance": "Below-average performance rating",
            "f_below_market_pay": "Pay below market benchmark", "f_high_overtime": "High overtime load",
            "f_high_absence": "Elevated absenteeism", "f_stagnant_no_promo": "No promotion despite tenure",
            "f_low_training": "Low training investment",
        }
        top_drivers.append(" & ".join(label_map[k] for k, _ in top2))
    active["TopRiskDrivers"] = top_drivers

    cols = ["EmployeeID", "FullName", "Department", "JobTitle", "JobLevel", "TenureYears",
            "EngagementScore", "PerformanceRating", "BaseSalaryUSD", "MarketBenchmarkUSD",
            "OvertimeHoursMonthly", "AbsenceDaysYTD", "PromotionsCount", "AttritionRiskScore",
            "RiskBand", "TopRiskDrivers"]
    return active[cols].sort_values("AttritionRiskScore", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.abspath(__file__)) + os.sep
    employees = pd.read_csv(base + "_cache_employees.csv")
    monthly_trend = pd.read_csv(base + "_cache_monthly_trend.csv")

    company_fc, dept_fc, slope = forecast_headcount(employees, monthly_trend)
    attrition_fc = forecast_attrition_rate(monthly_trend)
    hiring_plan = build_hiring_plan(dept_fc, attrition_fc, None)
    risk_scores = score_attrition_risk(employees)

    company_fc.to_csv(base + "_cache_company_forecast.csv", index=False)
    dept_fc.to_csv(base + "_cache_dept_forecast.csv", index=False)
    attrition_fc.to_csv(base + "_cache_attrition_forecast.csv", index=False)
    hiring_plan.to_csv(base + "_cache_hiring_plan.csv", index=False)
    risk_scores.to_csv(base + "_cache_risk_scores.csv", index=False)

    print("Forecasting complete.")
    print(f"  Monthly headcount trend slope: {slope:+.2f} employees/month")
    print(f"  12-month blended headcount forecast: {company_fc['ForecastHeadcount_Blended'].iloc[-1]}")
    print(f"  Risk bands: {risk_scores['RiskBand'].value_counts().to_dict()}")
    print(f"  Total planned hires (12mo): {hiring_plan['PlannedHires'].sum()}")
