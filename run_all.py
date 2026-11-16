"""Regenerate every table, figure, notebook and report from the data in data/. Run from the repo root: python run_all.py"""
import subprocess, sys
for step in ["scripts/01_data_overview.py", "scripts/02_monitoring.py", "scripts/03_recalibration.py",
             "scripts/04_validation_fairness_scope.py", "scripts/05_build_reports.py", "tools/build_notebooks.py"]:
    print(f"\n=== {step} ===", flush=True)
    subprocess.run([sys.executable, step], check=True)
print("\nDone. For PDFs: bash tools/make_pdfs.sh (needs wkhtmltopdf)")
