import csv
import os
from collections import Counter
from pathlib import Path
from tests.telemetry import test_results_log

def pytest_sessionfinish(session, exitstatus):
    """
    Hook that runs after all tests complete.
    Generates the results.csv and the Markdown summary report.
    """
    if not test_results_log:
        return

    # 1. Anchor strictly to the project root (one level up from this file)
    project_root = Path(__file__).parent.parent
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)
    
    # 2. Generate CSV
    csv_path = results_dir / "results.csv"
    keys = test_results_log[0].keys()
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(test_results_log)
        
    # 3. Calculate Aggregate Metrics
    total_runs = len(test_results_log)
    passed_runs = sum(1 for r in test_results_log if r["passed"])
    success_rate = (passed_runs / total_runs) * 100
    total_cost = sum(r["cost"] for r in test_results_log)
    avg_cost = total_cost / passed_runs if passed_runs else 0
    avg_steps = sum(r["steps"] for r in test_results_log) / total_runs
    
    failures = [r["failure_reasons"] for r in test_results_log if not r["passed"]]
    common_failures = Counter(failures).most_common(3)

    # 4. Generate Markdown Report
    md_path = results_dir / "run_summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 📊 Agent Reliability Harness - Run Summary\n\n")
        f.write("## 📈 Aggregate Metrics\n")
        f.write(f"- **Total Test Cases Executed:** {total_runs}\n")
        f.write(f"- **Success Rate:** {success_rate:.1f}%\n")
        f.write(f"- **Average Tool Steps:** {avg_steps:.2f}\n")
        f.write(f"- **Total Suite Token Cost:** ${total_cost:.5f}\n")
        f.write(f"- **Cost per Successful Run:** ${avg_cost:.5f}\n\n")
        
        f.write("## ⚠️ Top 3 Observed Failure Modes\n")
        if not common_failures:
            f.write("No failures observed. Agent is 100% reliable on this dataset.\n")
        else:
            for reason, count in common_failures:
                f.write(f"- **({count} instances):** {reason}\n")
                
    print(f"\n✅ Eval complete! Results exported to {csv_path} and {md_path}")