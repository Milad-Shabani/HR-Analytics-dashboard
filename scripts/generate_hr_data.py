"""
TelNova Communications - HR Workforce Analytics
Synthetic Data Generation Engine
=================================================
Generates a realistic, internally-consistent HR dataset for a fictional
Internet Service Provider / Telecom operator with:
    - ~750 employees (within the 500-1000 target band)
    - ~1,050,000 active broadband/mobile subscribers
    - 12 business functions typical of a converged telecom operator
    - 10 years of hiring, attrition, performance, engagement,
      training and recruitment history

All names, IDs and figures are FICTIONAL and generated with a fixed
random seed for full reproducibility. No real persons or companies
are represented.

Author: Milad Shabani
Project: TelNova HR Workforce Analytics
"""

import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
import random
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------
# 0. GLOBAL CONFIG
# ----------------------------------------------------------------------
SEED = 4217
np.random.seed(SEED)
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

TODAY = datetime(2026, 9, 1)                 # analysis "as-of" date
COMPANY_FOUNDED = datetime(2011, 3, 1)        # 15+ years of history
TOTAL_SUBSCRIBERS = 1_047_500                 # ~1M subscribers (fiber+mobile+TV)
TARGET_HEADCOUNT_TODAY = 742                  # current active employee count

CURRENCY = "USD"

# ----------------------------------------------------------------------
# 1. ORG STRUCTURE
# ----------------------------------------------------------------------
DEPARTMENTS = {
    "Customer Care & Call Center":      dict(weight=0.22, female_ratio=0.58, field=False, attrition_mult=1.55),
    "Field Operations & Installation":  dict(weight=0.20, female_ratio=0.10, field=True,  attrition_mult=1.35),
    "Network Engineering & Ops":        dict(weight=0.12, female_ratio=0.22, field=False, attrition_mult=0.75),
    "IT & Software Engineering":        dict(weight=0.10, female_ratio=0.30, field=False, attrition_mult=0.95),
    "Sales & Business Development":     dict(weight=0.10, female_ratio=0.40, field=False, attrition_mult=1.25),
    "Billing & Revenue Assurance":      dict(weight=0.06, female_ratio=0.50, field=False, attrition_mult=0.90),
    "Marketing & Brand":                dict(weight=0.04, female_ratio=0.55, field=False, attrition_mult=1.00),
    "Human Resources":                  dict(weight=0.04, female_ratio=0.62, field=False, attrition_mult=0.70),
    "Finance & Accounting":             dict(weight=0.04, female_ratio=0.48, field=False, attrition_mult=0.65),
    "Data & Cybersecurity":             dict(weight=0.03, female_ratio=0.28, field=False, attrition_mult=0.80),
    "Procurement & Supply Chain":       dict(weight=0.03, female_ratio=0.35, field=False, attrition_mult=0.85),
    "Legal & Regulatory Affairs":       dict(weight=0.02, female_ratio=0.50, field=False, attrition_mult=0.55),
}

JOB_LEVELS = [
    ("L1 - Associate",        0.28, 0),
    ("L2 - Professional",     0.27, 1),
    ("L3 - Senior",           0.18, 2),
    ("L4 - Lead / Supervisor",0.12, 3),
    ("L5 - Manager",          0.08, 4),
    ("L6 - Senior Manager",   0.04, 5),
    ("L7 - Director",         0.02, 6),
    ("L8 - VP",               0.008,7),
    ("L9 - Executive (C-level)",0.002,8),
]

JOB_TITLES = {
    "Customer Care & Call Center": ["Call Center Agent", "Senior Support Agent", "Technical Support Specialist",
                                     "Customer Retention Specialist", "Team Lead - Customer Care", "QA Analyst - Care",
                                     "Customer Care Manager", "Head of Customer Experience"],
    "Field Operations & Installation": ["Installation Technician", "Senior Field Technician", "Field Supervisor",
                                          "Fiber Splicing Technician", "Fleet & Logistics Coordinator",
                                          "Field Operations Manager", "Head of Field Operations"],
    "Network Engineering & Ops": ["NOC Engineer", "RF Engineer", "Core Network Engineer", "Network Planning Engineer",
                                    "Senior Network Architect", "Network Operations Manager", "Head of Network Engineering"],
    "IT & Software Engineering": ["Software Engineer", "Senior Software Engineer", "DevOps Engineer",
                                    "QA Engineer", "Data Engineer", "Engineering Manager", "Head of Engineering", "CTO"],
    "Sales & Business Development": ["Sales Executive", "Account Manager", "B2B Sales Specialist",
                                       "Channel Partner Manager", "Sales Team Lead", "Regional Sales Manager", "Head of Sales"],
    "Billing & Revenue Assurance": ["Billing Analyst", "Revenue Assurance Specialist", "Collections Officer",
                                      "Billing Systems Analyst", "Billing & RA Manager"],
    "Marketing & Brand": ["Marketing Specialist", "Digital Marketing Analyst", "Brand Manager", "Content Strategist",
                            "Marketing Manager", "Head of Marketing"],
    "Human Resources": ["HR Generalist", "Talent Acquisition Specialist", "L&D Specialist", "Compensation Analyst",
                          "HR Business Partner", "HR Manager", "Chief Human Resources Officer"],
    "Finance & Accounting": ["Accountant", "Financial Analyst", "FP&A Analyst", "Payroll Specialist",
                               "Finance Manager", "Chief Financial Officer"],
    "Data & Cybersecurity": ["SOC Analyst", "Cybersecurity Engineer", "Data Analyst", "Data Scientist",
                               "Information Security Manager", "Head of Data & Security"],
    "Procurement & Supply Chain": ["Procurement Officer", "Supply Chain Analyst", "Vendor Manager", "Procurement Manager"],
    "Legal & Regulatory Affairs": ["Legal Counsel", "Regulatory Affairs Specialist", "Compliance Officer", "Head of Legal"],
}

WORK_LOCATIONS = ["Headquarters - Capital City", "Regional Office - North", "Regional Office - South",
                   "Regional Office - East", "Field / On-site", "Remote"]

EMPLOYMENT_TYPES = [("Full-time", 0.86), ("Part-time", 0.07), ("Contract", 0.07)]

EDUCATION = [("High School", 0.12), ("Diploma / Vocational", 0.20), ("Bachelor's Degree", 0.48),
             ("Master's Degree", 0.18), ("PhD", 0.02)]

TERMINATION_REASONS_VOL = ["Better Compensation Elsewhere", "Career Growth Opportunity", "Relocation",
                            "Work-Life Balance", "Further Education", "Retirement", "Health Reasons", "Undisclosed"]
TERMINATION_REASONS_INVOL = ["Performance Management", "Restructuring / Redundancy", "Policy Violation",
                             "End of Contract", "Attendance Issues"]

RECRUITMENT_SOURCES = [("Employee Referral", 0.28), ("Company Career Site", 0.22), ("LinkedIn", 0.20),
                        ("Recruitment Agency", 0.15), ("Job Board", 0.10), ("University Fair", 0.05)]


def weighted_choice(options):
    labels = [o[0] for o in options]
    weights = [o[1] for o in options]
    return random.choices(labels, weights=weights, k=1)[0]


def pick_job_level_for_dept_role(title):
    """Assign a job level consistent with title seniority keywords."""
    t = title.lower()
    if any(k in t for k in ["chief", "cto", "cfo", "chro", "head of"]):
        return random.choice(["L8 - VP", "L9 - Executive (C-level)"])
    if "director" in t:
        return "L7 - Director"
    if "manager" in t and "team" not in t:
        return random.choice(["L5 - Manager", "L6 - Senior Manager"])
    if any(k in t for k in ["lead", "supervisor", "team lead"]):
        return "L4 - Lead / Supervisor"
    if any(k in t for k in ["senior", "specialist ii"]):
        return "L3 - Senior"
    if any(k in t for k in ["analyst", "engineer", "officer", "specialist", "agent", "technician", "counsel"]):
        return random.choices(["L1 - Associate", "L2 - Professional", "L3 - Senior"], weights=[0.35, 0.45, 0.20])[0]
    return "L2 - Professional"


LEVEL_BASE_SALARY = {
    "L1 - Associate": 14000, "L2 - Professional": 19000, "L3 - Senior": 26000,
    "L4 - Lead / Supervisor": 34000, "L5 - Manager": 46000, "L6 - Senior Manager": 62000,
    "L7 - Director": 85000, "L8 - VP": 120000, "L9 - Executive (C-level)": 175000,
}
LEVEL_RANK = {name: rank for name, _, rank in JOB_LEVELS}


def random_date_between(start, end):
    delta = end - start
    if delta.days <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta.days))


# ----------------------------------------------------------------------
# 2. GENERATE EMPLOYEE MASTER TABLE
# ----------------------------------------------------------------------
def generate_employees(n_active_target=TARGET_HEADCOUNT_TODAY):
    # Over the company's life, more people were hired than are currently active
    # (accounting for historical attrition). Estimate total headcount ever hired.
    total_ever_hired = int(n_active_target * 1.95)

    records = []
    emp_id_counter = 100001

    dept_names = list(DEPARTMENTS.keys())
    dept_weights = [DEPARTMENTS[d]["weight"] for d in dept_names]

    for i in range(total_ever_hired):
        emp_id = f"TN-{emp_id_counter}"
        emp_id_counter += 1

        dept = random.choices(dept_names, weights=dept_weights, k=1)[0]
        dept_cfg = DEPARTMENTS[dept]
        title = random.choice(JOB_TITLES[dept])
        level = pick_job_level_for_dept_role(title)
        level_rank = LEVEL_RANK[level]

        gender = "Female" if random.random() < dept_cfg["female_ratio"] else "Male"
        first_name = fake.first_name_female() if gender == "Female" else fake.first_name_male()
        last_name = fake.last_name()
        full_name = f"{first_name} {last_name}"

        # Hire date: weighted toward more recent years (company grew over time)
        years_since_founding = (TODAY - COMPANY_FOUNDED).days / 365.25
        growth_bias = np.random.beta(2.2, 1.3)  # skews toward later years -> growth curve
        hire_offset_days = int(growth_bias * (TODAY - COMPANY_FOUNDED).days)
        hire_date = COMPANY_FOUNDED + timedelta(days=hire_offset_days)
        if hire_date > TODAY - timedelta(days=14):
            hire_date = TODAY - timedelta(days=random.randint(14, 90))

        age_at_hire = max(20, int(np.random.normal(28 + level_rank * 1.6, 5)))
        birth_date = hire_date - timedelta(days=int(age_at_hire * 365.25))

        tenure_years_possible = (TODAY - hire_date).days / 365.25

        # Attrition hazard grows with tenure dissatisfaction curve & dept multiplier,
        # and shrinks with seniority (execs/directors churn far less).
        base_hazard = 0.145 * dept_cfg["attrition_mult"] * (1.0 - min(level_rank, 6) * 0.045)
        # probability employee has already left, given tenure window
        prob_left = 1 - np.exp(-base_hazard * tenure_years_possible)
        prob_left = min(prob_left, 0.93)

        is_terminated = random.random() < prob_left

        status = "Active"
        term_date, term_type, term_reason = None, None, None
        if is_terminated:
            status = "Terminated"
            term_offset_days = random.randint(60, max(61, (TODAY - hire_date).days - 1))
            term_date = hire_date + timedelta(days=term_offset_days)
            if term_date >= TODAY:
                term_date = TODAY - timedelta(days=random.randint(1, 30))
            term_type = "Voluntary" if random.random() < 0.72 else "Involuntary"
            term_reason = random.choice(TERMINATION_REASONS_VOL) if term_type == "Voluntary" else random.choice(TERMINATION_REASONS_INVOL)

        tenure_years = ((term_date if term_date else TODAY) - hire_date).days / 365.25

        # Compensation
        base_salary = LEVEL_BASE_SALARY[level]
        salary = base_salary * (1 + min(tenure_years, 12) * 0.028) * np.random.normal(1.0, 0.08)
        salary = round(max(salary, base_salary * 0.85), -2)
        market_benchmark = round(base_salary * np.random.normal(1.05, 0.05), -2)

        # Performance & engagement (correlated loosely with tenure/level, with noise)
        performance_rating = int(np.clip(np.random.normal(3.3 + level_rank * 0.05, 0.85), 1, 5))
        engagement_score = round(np.clip(np.random.normal(3.6 - (0.25 if status == "Terminated" and term_type == "Voluntary" else 0), 0.7), 1, 5), 1)

        overtime_hours = round(max(0, np.random.normal(8 if dept_cfg["field"] or "Call Center" in dept else 3, 5)), 1)
        training_hours_ytd = round(max(0, np.random.normal(24, 14)), 1)
        absence_days_ytd = int(max(0, np.random.normal(6 if dept_cfg["field"] else 4, 4)))

        promotions_count = np.random.poisson(min(tenure_years, 10) / 3.2)
        high_potential = "Yes" if (performance_rating >= 4 and engagement_score >= 3.8 and random.random() < 0.35) else "No"

        employment_type = weighted_choice(EMPLOYMENT_TYPES)
        education = weighted_choice(EDUCATION)
        work_location = "Field / On-site" if dept_cfg["field"] else random.choices(
            ["Headquarters - Capital City", "Regional Office - North", "Regional Office - South",
             "Regional Office - East", "Remote"], weights=[0.42, 0.16, 0.14, 0.14, 0.14])[0]

        records.append(dict(
            EmployeeID=emp_id, FullName=full_name, Gender=gender, BirthDate=birth_date.date(),
            Department=dept, JobTitle=title, JobLevel=level, LevelRank=level_rank,
            HireDate=hire_date.date(), EmploymentType=employment_type, WorkLocation=work_location,
            Education=education, Status=status, TerminationDate=term_date.date() if term_date else None,
            TerminationType=term_type, TerminationReason=term_reason,
            BaseSalaryUSD=salary, MarketBenchmarkUSD=market_benchmark,
            PerformanceRating=performance_rating, EngagementScore=engagement_score,
            OvertimeHoursMonthly=overtime_hours, TrainingHoursYTD=training_hours_ytd,
            AbsenceDaysYTD=absence_days_ytd, PromotionsCount=int(promotions_count),
            HighPotential=high_potential, TenureYears=round(tenure_years, 2),
        ))

    df = pd.DataFrame(records)

    # Assign managers: pick a higher-level employee from same department, if available
    df["ManagerID"] = None
    for dept in df["Department"].unique():
        dept_mask = (df["Department"] == dept) & (df["Status"] == "Active")
        dept_df = df[dept_mask]
        managers = dept_df[dept_df["LevelRank"] >= 4]
        if len(managers) == 0:
            continue
        idx_pool = dept_df[dept_df["LevelRank"] < 8].index
        for idx in idx_pool:
            candidate_managers = managers[managers["LevelRank"] > df.loc[idx, "LevelRank"]]
            if len(candidate_managers) > 0:
                df.loc[idx, "ManagerID"] = candidate_managers.sample(1)["EmployeeID"].values[0]

    return df


# ----------------------------------------------------------------------
# 3. RECRUITMENT REQUISITIONS (last 24 months)
# ----------------------------------------------------------------------
def generate_recruitment(employees_df, months_back=24):
    records = []
    req_id = 5001
    start_window = TODAY - timedelta(days=months_back * 30)

    # base number of hires per month scaled off actual hires in the data
    hires_recent = employees_df[pd.to_datetime(employees_df["HireDate"]) >= start_window]

    dept_names = list(DEPARTMENTS.keys())
    for _, hire_row in hires_recent.iterrows():
        dept = hire_row["Department"]
        title = hire_row["JobTitle"]
        hire_date = pd.to_datetime(hire_row["HireDate"])
        time_to_fill = int(np.clip(np.random.normal(34, 14), 9, 110))
        date_opened = hire_date - timedelta(days=time_to_fill)
        source = weighted_choice(RECRUITMENT_SOURCES)

        num_applicants = int(np.clip(np.random.normal(46, 28), 4, 220))
        num_interviewed = int(np.clip(num_applicants * np.random.uniform(0.12, 0.28), 2, num_applicants))
        num_offered = max(1, int(np.clip(num_interviewed * np.random.uniform(0.15, 0.35), 1, num_interviewed)))
        num_accepted = 1  # this requisition resulted in the observed hire

        cost_per_hire = round(np.clip(np.random.normal(1450 if "Manager" not in title and "Director" not in title else 3200, 500), 250, 9000), 0)

        records.append(dict(
            RequisitionID=f"REQ-{req_id}", Department=dept, JobTitle=title,
            DateOpened=date_opened.date(), DateFilled=hire_date.date(),
            TimeToFillDays=time_to_fill, Source=source,
            NumApplicants=num_applicants, NumInterviewed=num_interviewed,
            NumOffered=num_offered, NumAccepted=num_accepted,
            CostOfHireUSD=cost_per_hire, Status="Filled",
        ))
        req_id += 1

    # A handful of currently OPEN requisitions (not yet filled)
    for _ in range(random.randint(14, 22)):
        dept = random.choices(dept_names, weights=[DEPARTMENTS[d]["weight"] for d in dept_names], k=1)[0]
        title = random.choice(JOB_TITLES[dept])
        days_open = random.randint(3, 75)
        date_opened = TODAY - timedelta(days=days_open)
        num_applicants = int(np.clip(np.random.normal(40, 25), 3, 200))
        num_interviewed = int(np.clip(num_applicants * np.random.uniform(0.1, 0.25), 1, num_applicants))
        records.append(dict(
            RequisitionID=f"REQ-{req_id}", Department=dept, JobTitle=title,
            DateOpened=date_opened.date(), DateFilled=None,
            TimeToFillDays=None, Source=weighted_choice(RECRUITMENT_SOURCES),
            NumApplicants=num_applicants, NumInterviewed=num_interviewed,
            NumOffered=0, NumAccepted=0, CostOfHireUSD=None, Status="Open",
        ))
        req_id += 1

    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 4. ENGAGEMENT SURVEYS (last 8 quarters, sampled respondents)
# ----------------------------------------------------------------------
def generate_engagement(employees_df, quarters_back=8):
    records = []
    active = employees_df.copy()
    quarter_dates = [TODAY - timedelta(days=91 * q) for q in range(quarters_back)][::-1]

    for q_date in quarter_dates:
        eligible = active[pd.to_datetime(active["HireDate"]) <= q_date]
        eligible = eligible[(pd.to_datetime(eligible["TerminationDate"]).isna()) |
                             (pd.to_datetime(eligible["TerminationDate"]) >= q_date)]
        if len(eligible) == 0:
            continue
        respondents = eligible.sample(frac=np.random.uniform(0.65, 0.85), random_state=random.randint(1, 99999))
        for _, row in respondents.iterrows():
            base = row["EngagementScore"] if not pd.isna(row["EngagementScore"]) else 3.5
            overall = float(np.clip(np.random.normal(base, 0.4), 1, 5))
            enps_component = int(np.clip(np.random.normal((overall - 3) * 40, 20), -100, 100))
            records.append(dict(
                EmployeeID=row["EmployeeID"], Department=row["Department"], SurveyQuarter=q_date.strftime("%Y-Q") + str((q_date.month - 1)//3 + 1),
                SurveyDate=q_date.date(), OverallEngagement=round(overall, 1),
                eNPS_Response=enps_component,
                WorkLifeBalance=round(float(np.clip(np.random.normal(overall, 0.5), 1, 5)), 1),
                ManagerRelationship=round(float(np.clip(np.random.normal(overall + 0.1, 0.5), 1, 5)), 1),
                CareerGrowth=round(float(np.clip(np.random.normal(overall - 0.2, 0.6), 1, 5)), 1),
                CompensationSatisfaction=round(float(np.clip(np.random.normal(overall - 0.3, 0.6), 1, 5)), 1),
                CultureAndInclusion=round(float(np.clip(np.random.normal(overall + 0.05, 0.5), 1, 5)), 1),
            ))
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 5. TRAINING RECORDS
# ----------------------------------------------------------------------
TRAINING_COURSES = [
    ("Fiber Network Fundamentals", "Technical"), ("Advanced Customer De-escalation", "Soft Skills"),
    ("Leadership Essentials", "Leadership"), ("Cybersecurity Awareness", "Compliance"),
    ("Python for Analytics", "Technical"), ("Telecom Regulatory Compliance", "Compliance"),
    ("Sales Negotiation Mastery", "Sales"), ("Project Management Fundamentals", "Professional Development"),
    ("Diversity & Inclusion Workshop", "Culture"), ("Health & Safety for Field Teams", "Safety"),
    ("Cloud & DevOps Bootcamp", "Technical"), ("Coaching for Managers", "Leadership"),
]


def generate_training(employees_df):
    records = []
    active = employees_df[employees_df["Status"] == "Active"]
    train_id = 9001
    for _, row in active.iterrows():
        n_courses = np.random.poisson(1.6)
        for _ in range(n_courses):
            course, category = random.choice(TRAINING_COURSES)
            hours = round(np.clip(np.random.normal(8, 5), 1, 40), 1)
            completion_date = random_date_between(max(pd.to_datetime(row["HireDate"]).to_pydatetime(), TODAY - timedelta(days=365)), TODAY)
            cost = round(hours * np.random.uniform(35, 90), 0)
            records.append(dict(
                TrainingID=f"TRN-{train_id}", EmployeeID=row["EmployeeID"], Department=row["Department"],
                CourseName=course, Category=category, HoursCompleted=hours,
                CompletionDate=completion_date.date(), CostUSD=cost,
            ))
            train_id += 1
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# 6. MONTHLY HEADCOUNT TREND (last 36 months, reconstructed from hire/term dates)
# ----------------------------------------------------------------------
def generate_monthly_trend(employees_df, months_back=36):
    months = pd.date_range(end=TODAY, periods=months_back, freq="MS")
    records = []
    hire_dates = pd.to_datetime(employees_df["HireDate"])
    term_dates = pd.to_datetime(employees_df["TerminationDate"])

    for m in months:
        month_end = m + pd.offsets.MonthEnd(0)
        headcount = int(((hire_dates <= month_end) & (term_dates.isna() | (term_dates > month_end))).sum())
        hires = int(((hire_dates >= m) & (hire_dates <= month_end)).sum())
        terms = int(((term_dates >= m) & (term_dates <= month_end)).sum())
        vol_terms = int((((term_dates >= m) & (term_dates <= month_end)) & (employees_df["TerminationType"] == "Voluntary")).sum())
        records.append(dict(
            Month=m.date(), Headcount=headcount, Hires=hires, Terminations=terms,
            VoluntaryTerminations=vol_terms,
            SubscribersThousands=round((TOTAL_SUBSCRIBERS / 1000) * np.clip(np.random.normal(1 - (months_back - list(months).index(m)) * 0.004, 0.01), 0.7, 1.02), 1),
        ))
    return pd.DataFrame(records)


if __name__ == "__main__":
    print("Generating TelNova Communications synthetic HR dataset...")
    employees = generate_employees()
    print(f"  Employees generated (all-time): {len(employees)} | Active today: {(employees['Status']=='Active').sum()}")
    recruitment = generate_recruitment(employees)
    engagement = generate_engagement(employees)
    training = generate_training(employees)
    monthly_trend = generate_monthly_trend(employees)

    employees.to_csv(os.path.join(SCRIPT_DIR, "_cache_employees.csv"), index=False)
    recruitment.to_csv(os.path.join(SCRIPT_DIR, "_cache_recruitment.csv"), index=False)
    engagement.to_csv(os.path.join(SCRIPT_DIR, "_cache_engagement.csv"), index=False)
    training.to_csv(os.path.join(SCRIPT_DIR, "_cache_training.csv"), index=False)
    monthly_trend.to_csv(os.path.join(SCRIPT_DIR, "_cache_monthly_trend.csv"), index=False)
    print("Cached intermediate CSVs. Ready for forecast_engine.py and build_workbook.py")
