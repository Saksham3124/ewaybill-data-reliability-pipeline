"""
validation/reporter.py
----------------------
Markdown validation report generator conforming to Phase 4 specification.
Produces docs/validation_report.md summarizing test outcomes, categorizations,
affected entities, and REC-V01 to REC-V08 results.
"""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from src.validation.models import ValidationCheckResult, ValidationStatus


class ValidationReporter:
    """Generates structured markdown validation reports from check results."""

    @staticmethod
    def generate_report(
        results: List[ValidationCheckResult],
        run_id: str,
        output_file: str = "docs/validation_report.md"
    ) -> str:
        """Compiles and writes docs/validation_report.md."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.status == ValidationStatus.PASS.value)
        warning_checks = sum(1 for r in results if r.status == ValidationStatus.WARNING.value)
        failed_checks = sum(1 for r in results if r.status == ValidationStatus.FAIL.value)

        # Categorize
        by_category = Counter(r.check_category for r in results)
        cat_pass = Counter(r.check_category for r in results if r.status == ValidationStatus.PASS.value)
        cat_warn = Counter(r.check_category for r in results if r.status == ValidationStatus.WARNING.value)
        cat_fail = Counter(r.check_category for r in results if r.status == ValidationStatus.FAIL.value)

        # Affected tables
        affected_tables = sorted(list(set(r.table_name for r in results if r.status in (ValidationStatus.WARNING.value, ValidationStatus.FAIL.value))))
        total_affected_records = sum(r.affected_records for r in results if r.status in (ValidationStatus.WARNING.value, ValidationStatus.FAIL.value))

        md = []
        md.append("# Data Reliability & Validation Report")
        md.append("")
        md.append(f"**Pipeline Run ID:** `{run_id}`  ")
        md.append(f"**Execution Timestamp:** `{now_str}`  ")
        md.append(f"**Target Source:** `data/Road_EwayBill_2023_24.xlsx`  ")
        md.append(f"**Validation Framework:** Phase 4 Automated Validation Engine  ")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 1. Executive Summary")
        md.append("")
        md.append("| Metric | Count | Percentage |")
        md.append("| :--- | :---: | :---: |")
        md.append(f"| **Total Checks Executed** | **{total_checks}** | 100.0% |")
        md.append(f"| **Checks Passed** (`PASS`) | **{passed_checks}** | {passed_checks/total_checks*100:.1f}% |")
        md.append(f"| **Checks with Warnings** (`WARNING`) | **{warning_checks}** | {warning_checks/total_checks*100:.1f}% |")
        md.append(f"| **Checks Failed** (`FAIL`) | **{failed_checks}** | {failed_checks/total_checks*100:.1f}% |")
        md.append(f"| **Affected Tables** | **{len(affected_tables)}** | - |")
        md.append(f"| **Total Affected Records** | **{total_affected_records}** | - |")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 2. Checks by Validation Category")
        md.append("")
        md.append("| Category | Total Checks | Passed | Warnings | Failed | Category Health |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")

        for cat in sorted(by_category.keys()):
            tot = by_category[cat]
            p = cat_pass[cat]
            w = cat_warn[cat]
            f = cat_fail[cat]
            health = "HEALTHY" if f == 0 and w == 0 else ("WARNING" if f == 0 else "FAIL")
            md.append(f"| **{cat}** | {tot} | {p} | {w} | {f} | `{health}` |")

        md.append("")
        md.append("---")
        md.append("")
        md.append("## 3. Approved Source-Total Validations (REC-V01 through REC-V08)")
        md.append("")
        md.append("These 8 intra-table mathematical checks represent verified balance assertions explicitly supported by source layout and totals:")
        md.append("")
        md.append("| Rule ID | Check Name | Source Table | Status | Difference | Tolerance | Pass/Fail Rule |")
        md.append("| :---: | :--- | :--- | :---: | :---: | :---: | :--- |")

        rec_checks = [r for r in results if r.check_category == "SOURCE_TOTAL"]
        for r in rec_checks:
            diff_str = f"{r.difference:.8f}" if r.difference is not None else "0.0"
            md.append(f"| **{r.check_id}** | {r.check_name} | `{r.table_name}` | `{r.status}` | `{diff_str}` | `0.0001` | Difference $\\le$ Tolerance |")

        md.append("")
        md.append("---")
        md.append("")
        md.append("## 4. Comprehensive Validation Check Details")
        md.append("")
        md.append("| Check ID | Category | Check Name | Target Table | Status | Severity | Message |")
        md.append("| :---: | :--- | :--- | :--- | :---: | :---: | :--- |")

        for r in results:
            badge = f"`{r.status}`"
            sev = f"`{r.severity}`"
            msg = r.message.replace("\n", " ").replace("|", "\\|")
            md.append(f"| **{r.check_id}** | {r.check_category} | {r.check_name} | `{r.table_name}` | {badge} | {sev} | {msg} |")

        md.append("")
        md.append("---")
        md.append("")
        md.append("## 5. Architectural Status of Trusted Layer")
        md.append("")
        md.append("> [!IMPORTANT]")
        md.append("> **ARCHITECTURAL GOVERNANCE RULE:**  ")
        md.append("> In accordance with Phase 4 governance requirements, the `trusted_*` tables currently hold normalized/staging representations. They must **NOT** be certified as production-approved trusted data until complete cross-table reconciliation and methodology verification (Phase 5) have been completed.")

        report_content = "\n".join(md)
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return report_content
