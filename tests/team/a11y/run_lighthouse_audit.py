"""
Lighthouse Audit Runner for Frappe CRM Leads and Deals Screens.
Executes Google Lighthouse across:
- Accessibility (WCAG compliance, ARIA attributes, color contrast)
- Best Practices (Security, HTML doctype, viewport, console logging)
- SEO (Meta tags, title, crawling landmarks)

Generates JSON and HTML audit reports in docs/lighthouse/.
"""

import os
import sys
import json
import time
import subprocess
import threading
import socketserver

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from tests.team.e2e.mock_server import MockCRMHandler, PORT

CHROME_EXE = r"C:\Users\uh723\AppData\Local\ms-playwright\chromium-1255\chrome-win64\chrome.exe"
LIGHTHOUSE_CLI = r"C:\Users\uh723\AppData\Roaming\npm\lighthouse.cmd"
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "lighthouse")


def start_server():
    server = socketserver.TCPServer(("127.0.0.1", PORT), MockCRMHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    return server


def run_audit_for_url(url: str, output_base: str):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    output_path = os.path.join(REPORTS_DIR, output_base)

    env = os.environ.copy()
    env["CHROME_PATH"] = CHROME_EXE

    cmd = [
        f'"{LIGHTHOUSE_CLI}"',
        url,
        "--output=json",
        "--output=html",
        f'--output-path="{output_path}"',
        "--only-categories=accessibility,best-practices,seo",
        '--chrome-flags="--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage"',
        "--quiet"
    ]

    print(f"Running Lighthouse on: {url} -> {output_base}")
    proc = subprocess.run(" ".join(cmd), env=env, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Warning: Lighthouse exited with code {proc.returncode}:\n{proc.stderr}")

    json_file = f"{output_path}.report.json"
    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        categories = data.get("categories", {})
        scores = {
            cat: int((categories[cat].get("score") or 0) * 100)
            for cat in ["accessibility", "best-practices", "seo"]
            if cat in categories
        }
        return scores
    return {}


def main():
    server = start_server()
    results = {}
    try:
        # Audit 1: Lead Screen
        results["Lead Screen"] = run_audit_for_url(
            f"http://127.0.0.1:{PORT}/", "lead_screen"
        )
        # Audit 2: Deal Screen
        results["Deal Screen"] = run_audit_for_url(
            f"http://127.0.0.1:{PORT}/deal", "deal_screen"
        )
    finally:
        server.shutdown()

    print("\n" + "=" * 50)
    print("LIGHTHOUSE AUDIT SUMMARY SCORES")
    print("=" * 50)
    for screen, scores in results.items():
        print(f"\n{screen}:")
        for cat, score in scores.items():
            print(f"  - {cat.replace('-', ' ').title()}: {score}/100")
    print("=" * 50)

    summary_file = os.path.join(REPORTS_DIR, "lighthouse_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved summary to: {summary_file}")


if __name__ == "__main__":
    main()
