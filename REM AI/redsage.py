import subprocess
import json
import os
import logging

class RedSageAgent:
    """
    RedSage: REM AI's specialized Multi-Agent Security Specialist.
    Orchestrates static analysis and vulnerability triage.
    """
    def __init__(self):
        self.bandit_path = r'C:\Users\07kav\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\bandit.exe'
        self.report_path = "bandit_report.json"

    def run_scan(self):
        """Executes a Bandit scan on the codebase."""
        logging.info("[RED_SAGE] Initiating core scan...")
        try:
            # Run bandit scan
            cmd = [self.bandit_path, "-r", ".", "-f", "json", "-o", self.report_path]
            subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(self.report_path):
                with open(self.report_path, "r") as f:
                    return json.load(f)
            return {"error": "Scan failed to generate report."}
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
