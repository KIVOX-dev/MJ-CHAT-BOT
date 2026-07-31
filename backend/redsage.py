import shutil
import subprocess
import json
import os
import time
import threading
import logging


class RedSageRateLimitError(Exception):
    """Raised when an identity triggers RedSage faster than MIN_INTERVAL_SECONDS."""


class RedSageAgent:
    """
    RedSage: REM AI's specialized Multi-Agent Security Specialist.
    Orchestrates static analysis and vulnerability triage.

    This runs a subprocess over the whole codebase, so it's gated two ways:
    reaching it at all requires the same bearer-token auth as every other
    /api/chat call (see auth.py), and check_rate_limit() additionally caps
    how often any single identity can trigger a scan, since a scan is
    comparatively expensive and someone with a valid token could otherwise
    spam it.
    """
    MIN_INTERVAL_SECONDS = 120
    SCAN_TIMEOUT_SECONDS = 120

    _last_run_by_identity = {}
    _lock = threading.Lock()

    def __init__(self):
        # Resolved from PATH instead of a hardcoded developer-machine path -
        # the previous C:\Users\...\bandit.exe only ever worked on the
        # original author's machine.
        self.bandit_path = shutil.which("bandit")
        self.report_path = "bandit_report.json"

    @classmethod
    def check_rate_limit(cls, identity: str) -> None:
        """Raises RedSageRateLimitError if `identity` scanned too recently."""
        now = time.time()
        with cls._lock:
            last_run = cls._last_run_by_identity.get(identity, 0.0)
            elapsed = now - last_run
            if elapsed < cls.MIN_INTERVAL_SECONDS:
                wait_s = round(cls.MIN_INTERVAL_SECONDS - elapsed)
                raise RedSageRateLimitError(
                    f"RedSage scans are limited to one every {cls.MIN_INTERVAL_SECONDS}s per user. "
                    f"Try again in {wait_s}s."
                )
            cls._last_run_by_identity[identity] = now

    def run_scan(self):
        """Executes a Bandit scan on the codebase. Fails gracefully if Bandit isn't installed."""
        if not self.bandit_path:
            return {
                "error": (
                    "Bandit is not installed or not on PATH. "
                    "Install it with `pip install bandit` to enable RedSage scans."
                )
            }

        logging.info("[RED_SAGE] Initiating core scan...")
        try:
            cmd = [self.bandit_path, "-r", ".", "-f", "json", "-o", self.report_path]
            subprocess.run(cmd, capture_output=True, text=True, timeout=self.SCAN_TIMEOUT_SECONDS)

            if os.path.exists(self.report_path):
                with open(self.report_path, "r") as f:
                    return json.load(f)
            return {"error": "Scan failed to generate report."}
        except subprocess.TimeoutExpired:
            return {"error": f"Bandit scan timed out after {self.SCAN_TIMEOUT_SECONDS}s."}
        except Exception as e:
            return {"error": str(e)}

    def generate_audit_report(self):
        """Parses scan results and generates a RedSage Audit markdown."""
        data = self.run_scan()
        if "error" in data:
            return f"### RedSage Scan Error\n{data['error']}"

        results = data.get("results", [])

        report = "# RedSage Security Audit Report\n\n"
        report += f"**Scanned At**: {data.get('generated_at', 'Unknown')}\n\n"

        if not results:
            report += "> [!NOTE]\n> No vulnerabilities detected in the current scan scope. Clean bill of health!\n"
            return report

        # Tally severities
        severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for r in results:
            sev = r.get("issue_severity", "LOW")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        report += "## Executive Summary\n"
        report += f"- High Severity: {severity_counts['HIGH']}\n"
        report += f"- Medium Severity: {severity_counts['MEDIUM']}\n"
        report += f"- Low Severity: {severity_counts['LOW']}\n\n"

        report += "## Detailed Findings\n"
        for r in results:
            sev_label = "[HIGH]" if r["issue_severity"] == "HIGH" else "[MEDIUM]" if r["issue_severity"] == "MEDIUM" else "[LOW]"
            report += f"### {sev_label} {r['issue_text']}\n"
            report += f"- **File**: `{r['filename']}` (Line {r['line_number']})\n"
            report += f"- **CWE**: [{r['issue_cwe']['id']}]({r['issue_cwe']['link']})\n"
            report += f"- **Confidence**: {r['issue_confidence']}\n"
            report += f"- **Context**:\n```python\n{r['code'].strip()}\n```\n"
            report += "---\n"

        return report

if __name__ == "__main__":
    rs = RedSageAgent()
    print(rs.generate_audit_report())
