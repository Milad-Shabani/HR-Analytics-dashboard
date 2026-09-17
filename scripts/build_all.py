"""
TelNova Communications - HR Workforce Analytics
Pipeline Orchestrator
=================================================
Runs the full data pipeline end-to-end:

    1. generate_hr_data.py   -> synthesizes the raw HR dataset
    2. forecast_engine.py    -> workforce forecast, attrition forecast,
                                 hiring plan, individual risk scoring
    3. build_workbook.py     -> assembles data/HR_Analytics_Workbook.xlsx

Usage:
    python scripts/build_all.py

The companion dashboard (dashboard/index.html) reads the resulting
workbook directly in the browser -- no further build step is needed
for it. See README.md for how to view the dashboard locally.

Author: Milad Shabani
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
STEPS = ["generate_hr_data.py", "forecast_engine.py", "build_workbook.py"]
POST_RECALC_STEPS = ["export_dashboard_data.py"]
WORKBOOK_PATH = os.path.join(PROJECT_ROOT, "data", "HR_Analytics_Workbook.xlsx")
RECALC_SCRIPT_CANDIDATES = [
    "/mnt/skills/public/xlsx/scripts/recalc.py",  # available in Claude's sandbox
]


def try_recalculate():
    """Recalculate formulas with LibreOffice if it's installed locally.
    This is optional: openpyxl already writes correct formulas, LibreOffice
    just also bakes in cached values so the file opens with numbers visible
    in viewers that don't auto-calculate (and so the browser dashboard,
    which reads cached values via SheetJS, always has something to show).
    """
    has_soffice = subprocess.run(["which", "soffice"], capture_output=True).returncode == 0
    if not has_soffice:
        print("\n(Optional) LibreOffice ('soffice') not found -- skipping formula recalculation.")
        print("Open the workbook in Excel/LibreOffice once and save it, or install LibreOffice")
        print("and re-run this script, so cached formula values are baked in for the dashboard.")
        return
    for candidate in RECALC_SCRIPT_CANDIDATES:
        if os.path.exists(candidate):
            print("\n>>> Recalculating formulas with LibreOffice ...")
            subprocess.run([sys.executable, candidate, WORKBOOK_PATH, "90"])
            return


def main():
    print("=" * 70)
    print("TelNova Communications - HR Workforce Analytics: Build Pipeline")
    print("=" * 70)
    for step in STEPS:
        path = os.path.join(SCRIPT_DIR, step)
        print(f"\n>>> Running {step} ...")
        result = subprocess.run([sys.executable, path], cwd=SCRIPT_DIR)
        if result.returncode != 0:
            print(f"\nPipeline stopped: {step} exited with code {result.returncode}")
            sys.exit(result.returncode)

    try_recalculate()

    for step in POST_RECALC_STEPS:
        path = os.path.join(SCRIPT_DIR, step)
        print(f"\n>>> Running {step} ...")
        result = subprocess.run([sys.executable, path], cwd=SCRIPT_DIR)
        if result.returncode != 0:
            print(f"\nPipeline stopped: {step} exited with code {result.returncode}")
            sys.exit(result.returncode)

    print("\n" + "=" * 70)
    print("Done. Workbook written to data/HR_Analytics_Workbook.xlsx")
    print("Dashboard data snapshot written to dashboard/data.js")
    print("Open dashboard/index.html directly in a browser -- no server required.")
    print("(Use the 'Reload live from Excel' button when serving this project over http/https.)")
    print("=" * 70)


if __name__ == "__main__":
    main()
