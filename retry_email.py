
import os
import glob
from email_report import send_report

# Find the latest report file
list_of_files = glob.glob('godrej_complete_*.xlsx')
if not list_of_files:
    print("No report file found to send.")
    exit(1)

latest_file = max(list_of_files, key=os.path.getctime)
print(f"Resending latest report: {latest_file}")

# Simple body to test
body = """
Retrying email delivery for Godrej Scraper Report.
Previous attempt failed due to encoding issues.

Please find the report attached.
"""

success = send_report(
    latest_file,
    subject=f"Retry: Godrej Report - {latest_file}",
    body=body
)

if success:
    print("✓ Email retry successful!")
else:
    print("❌ Email retry failed.")
