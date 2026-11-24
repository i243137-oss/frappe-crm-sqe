"""
Runner Script for k6 Load Testing & Benchmark Reporting.
Executes 4 benchmark runs against Frappe CRM Lead Conversion API:
1. 1 VU Baseline (Run 1, 60s)
2. 1 VU Baseline (Run 2, 60s)
3. 5 VUs Load Test (Run 1, 60s)
4. 5 VUs Load Test (Run 2, 60s)

Gathers p95 latency, average latency, requests per second (RPS),
total request count, and failure percentage.
Outputs reports into docs/performance/.
"""

import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from tests.team.e2e.mock_server import MockCRMHandler, ReusableTCPServer, PORT

K6_EXE = r"C:\Program Files\k6\k6.exe"
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "k6_lead_conversion.js")
DOCS_PERF_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "performance")


def start_server():
    server = ReusableTCPServer(("127.0.0.1", PORT), MockCRMHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    return server


def execute_k6_run(vus: int, duration: str, run_id: str) -> dict:
    os.makedirs(DOCS_PERF_DIR, exist_ok=True)
    json_summary_file = os.path.join(DOCS_PERF_DIR, f"k6_{vus}vu_run{run_id}.json")

    cmd = [
        f'"{K6_EXE}"',
        "run",
        f"-e VUS={vus}",
        f"-e DURATION={duration}",
        f'--summary-export="{json_summary_file}"',
        f'"{SCRIPT_PATH}"',
    ]

    print(f"\n=======================================================")
    print(f"Starting k6 Benchmark: {vus} VU(s) | Duration: {duration} | Run #{run_id}")
    print(f"=======================================================")

    proc = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)

    # Parse k6 summary JSON
    metrics_summary = {}
    if os.path.exists(json_summary_file):
        with open(json_summary_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        metrics = data.get("metrics", {})
        dur = metrics.get("http_req_duration", {})
        reqs = metrics.get("http_reqs", {})
        failed = metrics.get("http_req_failed", {})

        metrics_summary = {
            "vus": vus,
            "run": run_id,
            "duration": duration,
            "total_requests": int(reqs.get("count", 0)),
            "rps": round(reqs.get("rate", 0), 2),
            "latency_avg_ms": round(dur.get("avg", 0), 2),
            "latency_p95_ms": round(dur.get("p(95)", 0), 2),
            "latency_max_ms": round(dur.get("max", 0), 2),
            "failure_rate_pct": round(failed.get("value", 0) * 100, 2),
        }
    return metrics_summary


def main():
    server = start_server()
    all_results = []
    try:
        # Config 1: 1 VU (Two runs of 60s each)
        r1_1vu = execute_k6_run(vus=1, duration="60s", run_id="1")
        all_results.append(r1_1vu)

        r2_1vu = execute_k6_run(vus=1, duration="60s", run_id="2")
        all_results.append(r2_1vu)

        # Config 2: 5 VUs (Two runs of 60s each)
        r1_5vu = execute_k6_run(vus=5, duration="60s", run_id="1")
        all_results.append(r1_5vu)

        r2_5vu = execute_k6_run(vus=5, duration="60s", run_id="2")
        all_results.append(r2_5vu)

    finally:
        server.shutdown()
        server.server_close()

    summary_file = os.path.join(DOCS_PERF_DIR, "k6_benchmark_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 70)
    print("CONSOLIDATED K6 PERFORMANCE BENCHMARK RESULTS")
    print("=" * 70)
    print(f"{'Config':<15} {'Reqs':<10} {'RPS':<10} {'Avg Latency':<14} {'p95 Latency':<14} {'Fail %':<8}")
    print("-" * 70)
    for r in all_results:
        label = f"{r['vus']} VU (Run {r['run']})"
        print(f"{label:<15} {r['total_requests']:<10} {r['rps']:<10} {r['latency_avg_ms']:<7} ms   {r['latency_p95_ms']:<7} ms   {r['failure_rate_pct']}%")
    print("=" * 70)
    print(f"Summary JSON saved to: {summary_file}")


if __name__ == "__main__":
    main()
