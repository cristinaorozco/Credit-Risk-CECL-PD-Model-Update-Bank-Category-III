#!/usr/bin/env bash
# Convert the HTML reports to PDF (needs wkhtmltopdf). Run after scripts/05_build_reports.py.
cd "$(dirname "$0")/../reports" || exit 1
for f in *.html; do wkhtmltopdf -q --enable-local-file-access -s Letter -T 15mm -B 15mm -L 14mm -R 14mm "$f" "${f%.html}.pdf"; done
