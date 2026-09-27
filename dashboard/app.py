"""
dashboard/app.py
----------------
Streamlit Operational Reliability Dashboard for the DGCI&S E-Way Bill Pipeline.

Guarantees & Constraints:
- Purely read-only interface (SELECT queries only).
- Consumes existing PostgreSQL results; never recalculates validation, reconciliation, or statistics.
- Never mutates incidents or triggers Airflow runs.
- Strictly adheres to epistemic boundaries:
  * STATISTICALLY_DIFFERENT is an advisory distributional signal, not a pipeline failure.
  * REC-DO06 / OTHER TERRITORY is an advisory UNRESOLVED finding, not an operational failure.
  * No composite reliability scores, no arbitrary health percentages, and no entity rankings.
"""

import os
import sys
from datetime import datetime
import pandas as pd
import streamlit as st

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.data_access import (
    fetch_pipeline_runs,
    fetch_latest_run_summary,
    fetch_validation_results,
    fetch_reconciliation_results,
    fetch_statistical_results,
    fetch_incidents,
    fetch_trusted_counts
)

PAGES = [
    "📊 Overview",
    "🔍 Data Quality",
    "⚖️ Reconciliation",
    "📈 Year-over-Year Statistics",
    "🚨 Incidents",
    "⏱️ Pipeline Runs"
]


def render_status_badge(status: str) -> str:
    s = str(status).upper()
    if s in ("SUCCESS", "PASS", "NO_MATERIAL_STATISTICAL_CHANGE", "RESOLVED"):
        return f"🟢 **{s}**"
    elif s in ("FAILED", "FAIL", "CRITICAL", "OPEN"):
        return f"🔴 **{s}**"
    elif s in ("UNRESOLVED", "WARNING", "STATISTICALLY_DIFFERENT", "ERROR", "HIGH"):
        return f"🟡 **{s}**"
    elif s in ("RUNNING", "ACKNOWLEDGED", "INFO"):
        return f"🔵 **{s}**"
    return f"⚪ **{s}**"


# =============================================================================
# PAGE A: OVERVIEW
# =============================================================================

def render_overview():
    st.title("📊 Reliability Platform Overview")
    st.markdown("Operational inspection and current status of the E-Way Bill batch reliability pipeline.")

    try:
        latest = fetch_latest_run_summary()
        runs_df = fetch_pipeline_runs()
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return

    if not latest:
        st.info("No pipeline execution runs found in the warehouse database.")
        return

    run_id = latest["run_id"]
    status = latest["status"]
    started_at = latest["started_at"]
    completed_at = latest["completed_at"]
    duration = latest["duration_seconds"]
    source_file = latest["source_filename"]

    # Top KPI Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(label="Latest Run Status", value=status, delta="Execution State")
    with col2:
        val_df = fetch_validation_results(run_id=run_id)
        pass_val = (val_df["status"] == "PASS").sum() if not val_df.empty else 0
        total_val = len(val_df)
        st.metric(label="Quality Checks", value=f"{pass_val}/{total_val}", delta="Passing")
    with col3:
        rec_df = fetch_reconciliation_results(run_id=run_id)
        unres_rec = (rec_df["status"] == "UNRESOLVED").sum() if not rec_df.empty else 0
        rec_status_text = "100% Resolved" if unres_rec == 0 else f"{unres_rec} Advisory Unresolved"
        st.metric(label="Reconciliation", value=rec_status_text, delta="Advisory Audits")
    with col4:
        stat_df = fetch_statistical_results(run_id=run_id)
        shift_count = (stat_df["status"] == "STATISTICALLY_DIFFERENT").sum() if not stat_df.empty else 0
        st.metric(label="YoY Shift Signals", value=f"{shift_count} Significant", delta="Distribution Drift")
    with col5:
        inc_df = fetch_incidents(status="OPEN")
        open_inc = len(inc_df)
        st.metric(label="Open Incidents", value=open_inc, delta="Requires Triage" if open_inc > 0 else "Normal")

    st.divider()

    # Detailed Latest Run Card
    c_left, c_right = st.columns([2, 1])

    with c_left:
        st.subheader("Latest Pipeline Run Details")
        st.markdown(f"- **Execution Run ID:** `{run_id}`")
        st.markdown(f"- **Source Workbook:** `{source_file}`")
        st.markdown(f"- **Started At:** `{started_at}`")
        st.markdown(f"- **Completed At:** `{completed_at or 'In Progress'}`")
        st.markdown(f"- **Duration:** `{duration} seconds`" if duration else "- **Duration:** `N/A`")

        # Promotion status
        trusted = fetch_trusted_counts(run_id)
        total_trusted_rows = sum(trusted.values())
        if status == "SUCCESS" and total_trusted_rows > 0:
            st.success(f"✅ **Trusted Data Promoted:** {total_trusted_rows:,} normalized records loaded across 5 golden tables.")
        elif status == "FAILED":
            st.error("🛑 **Trusted Data Promotion Halted:** Integrity failures triggered incident workflow.")
        else:
            st.warning("⏳ **Staging / Unpromoted:** Pipeline is currently executing or awaiting verification.")

    with c_right:
        st.subheader("Trusted Tables Row Counts")
        if trusted:
            t_df = pd.DataFrame(list(trusted.items()), columns=["Table Name", "Row Count"])
            st.dataframe(t_df, use_container_width=True, hide_index=True)
        else:
            st.write("No trusted rows recorded.")

    st.divider()

    # Quick Summary Tables
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.subheader("Validation Category Breakdown (Latest Run)")
        if not val_df.empty:
            cat_summary = val_df.groupby(["check_category", "status"]).size().unstack(fill_value=0)
            st.dataframe(cat_summary, use_container_width=True)
        else:
            st.write("No validation records for latest run.")

    with s_col2:
        st.subheader("Recent Execution History")
        if not runs_df.empty:
            mini_runs = runs_df[["run_id", "status", "started_at", "duration_seconds"]].head(5)
            st.dataframe(mini_runs, use_container_width=True, hide_index=True)


# =============================================================================
# PAGE B: DATA QUALITY
# =============================================================================

def render_data_quality():
    st.title("🔍 Data Quality Validation")
    st.markdown("Inspection of the 64 deterministic data-integrity rules across Schema, Completeness, Uniqueness, Domain, Numeric, Structural, and Source Totals.")

    runs_df = fetch_pipeline_runs()
    run_options = ["ALL"] + list(runs_df["run_id"].unique()) if not runs_df.empty else ["ALL"]

    # Filter Controls
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        sel_run = st.selectbox("Pipeline Run", run_options, index=1 if len(run_options) > 1 else 0)
    with f2:
        sel_cat = st.selectbox(
            "Validation Category",
            ["ALL", "SCHEMA", "COMPLETENESS", "UNIQUENESS", "DOMAIN", "NUMERIC", "STRUCTURAL", "SOURCE_TOTAL"]
        )
    with f3:
        sel_status = st.selectbox("Status", ["ALL", "PASS", "FAIL", "WARNING"])
    with f4:
        sel_table = st.selectbox(
            "Source Table",
            ["ALL", "table_i_interstate", "table_ii_state", "table_iii_outward", "table_iv_inward", "table_v_internal"]
        )

    val_df = fetch_validation_results(
        run_id=sel_run,
        table_name=sel_table,
        check_category=sel_cat,
        status=sel_status
    )

    # Metrics Summary
    total_checks = len(val_df)
    pass_count = (val_df["status"] == "PASS").sum() if total_checks > 0 else 0
    fail_count = (val_df["status"] == "FAIL").sum() if total_checks > 0 else 0
    warn_count = (val_df["status"] == "WARNING").sum() if total_checks > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Filtered Checks", total_checks)
    m2.metric("Passed Checks", pass_count)
    m3.metric("Failed Checks", fail_count)
    m4.metric("Warnings", warn_count)

    st.divider()

    if val_df.empty:
        st.info("No validation results matching the selected filters.")
    else:
        if sel_cat == "ALL" and sel_status == "ALL":
            st.subheader("Category Breakdown")
            cat_table = val_df.groupby(["check_category", "status"]).size().unstack(fill_value=0).reset_index()
            st.dataframe(cat_table, use_container_width=True, hide_index=True)

        st.subheader("Detailed Validation Audit Results")
        display_cols = [
            "check_id", "check_category", "table_name", "check_name",
            "status", "severity", "expected_value", "observed_value",
            "difference", "affected_records", "message"
        ]
        st.dataframe(
            val_df[display_cols],
            use_container_width=True,
            hide_index=True
        )


# =============================================================================
# PAGE C: RECONCILIATION
# =============================================================================

def render_reconciliation():
    st.title("⚖️ Cross-Table Reconciliation Engine")
    st.markdown("Advisory audits of mathematical relationships observed across national aggregates, trade flow conservation, and state marginal totals.")

    runs_df = fetch_pipeline_runs()
    run_options = ["ALL"] + list(runs_df["run_id"].unique()) if not runs_df.empty else ["ALL"]

    c1, c2, c3 = st.columns(3)
    with c1:
        sel_run = st.selectbox("Pipeline Run", run_options, index=1 if len(run_options) > 1 else 0)
    with c2:
        sel_rule = st.selectbox(
            "Reconciliation Rule",
            ["ALL", "REC-DO01", "REC-DO02", "REC-DO03", "REC-DO04", "REC-DO05", "REC-DO06"]
        )
    with c3:
        sel_status = st.selectbox("Status", ["ALL", "PASS", "UNRESOLVED", "WARNING", "FAIL"])

    rec_df = fetch_reconciliation_results(run_id=sel_run, rule_code=sel_rule, status=sel_status)

    total_rec = len(rec_df)
    pass_rec = (rec_df["status"] == "PASS").sum() if total_rec > 0 else 0
    unres_rec = (rec_df["status"] == "UNRESOLVED").sum() if total_rec > 0 else 0
    fail_rec = (rec_df["status"] == "FAIL").sum() if total_rec > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Audits", total_rec)
    m2.metric("Resolved / Passed", pass_rec)
    m3.metric("Advisory Unresolved", unres_rec)
    m4.metric("Failed", fail_rec)

    st.divider()

    # Explicit Governance Banner for OTHER TERRITORY / REC-DO06
    st.info(
        "📌 **Advisory Audit Policy (REC-DO06 / OTHER TERRITORY):**  \n"
        "`OTHER TERRITORY` in Table IV (Inward) contains ₹3,030.56 crore not present in Table II or Table III. "
        "Under current governance rules, this is recorded as an **UNRESOLVED non-blocking** finding. "
        "It faithfully reflects official published figures and does NOT fail the pipeline or halt trusted data promotion."
    )

    if rec_df.empty:
        st.info("No reconciliation records matching the selected filters.")
    else:
        st.subheader("Cross-Table Audit Records")
        display_cols = [
            "rule_code", "rule_category", "source_tables", "dimension",
            "entity", "expected_value", "observed_value", "absolute_difference",
            "relative_difference", "absolute_tolerance", "status", "severity", "message"
        ]
        st.dataframe(
            rec_df[display_cols],
            use_container_width=True,
            hide_index=True
        )


# =============================================================================
# PAGE D: YEAR-OVER-YEAR STATISTICS
# =============================================================================

def render_statistics():
    st.title("📈 Year-over-Year Statistical Analysis")
    st.markdown("Annual snapshot comparison between **FY 2022–23** and **FY 2023–24**.")

    # Mandatory Epistemic Banner
    st.info(
        "ℹ️ **Informational Guidance:**  \n"
        "STATISTICALLY_DIFFERENT indicates an observed distributional difference under the configured analysis. "
        "It does not by itself indicate data corruption or pipeline failure."
    )

    runs_df = fetch_pipeline_runs()
    run_options = ["ALL"] + list(runs_df["run_id"].unique()) if not runs_df.empty else ["ALL"]

    c1, c2, c3 = st.columns(3)
    with c1:
        sel_run = st.selectbox("Pipeline Run", run_options, index=1 if len(run_options) > 1 else 0)
    with c2:
        sel_method = st.selectbox("Test Method", ["ALL", "YOY_CHANGE", "KS_TEST", "PSI", "CROSS_YEAR_OBSERVATION"])
    with c3:
        sel_status = st.selectbox(
            "Statistical Status",
            ["ALL", "NO_MATERIAL_STATISTICAL_CHANGE", "STATISTICALLY_DIFFERENT", "INSUFFICIENT_DATA", "NOT_APPLICABLE"]
        )

    stat_df = fetch_statistical_results(run_id=sel_run, test_method=sel_method, status=sel_status)

    total_stat = len(stat_df)
    stable_count = (stat_df["status"] == "NO_MATERIAL_STATISTICAL_CHANGE").sum() if total_stat > 0 else 0
    shifted_count = (stat_df["status"] == "STATISTICALLY_DIFFERENT").sum() if total_stat > 0 else 0
    other_count = total_stat - stable_count - shifted_count

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Evaluated Metrics", total_stat)
    m2.metric("No Material Change", stable_count)
    m3.metric("Statistically Different", shifted_count)
    m4.metric("Insufficient / N/A", other_count)

    st.divider()

    if stat_df.empty:
        st.info("No statistical analysis results matching the selected filters.")
    else:
        st.subheader("Statistical Evaluation Details")
        display_cols = [
            "comparison_year", "reference_year", "dimension", "metric",
            "test_method", "sample_size_reference", "sample_size_comparison",
            "statistic", "p_value", "psi_value", "status", "interpretation"
        ]
        st.dataframe(
            stat_df[display_cols],
            use_container_width=True,
            hide_index=True
        )


# =============================================================================
# PAGE E: INCIDENTS
# =============================================================================

def render_incidents():
    st.title("🚨 Operational Incidents")
    st.markdown("Inspection of pipeline failures, root causes, and alert dispatch history.")

    runs_df = fetch_pipeline_runs()
    run_options = ["ALL"] + list(runs_df["run_id"].unique()) if not runs_df.empty else ["ALL"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_sev = st.selectbox("Severity", ["ALL", "CRITICAL", "ERROR", "WARNING"])
    with c2:
        sel_status = st.selectbox("Status", ["ALL", "OPEN", "ACKNOWLEDGED", "RESOLVED"])
    with c3:
        sel_run = st.selectbox("Pipeline Run", run_options)
    with c4:
        sel_table = st.selectbox(
            "Source Table",
            ["ALL", "table_i_interstate", "table_ii_state", "table_iii_outward", "table_iv_inward", "table_v_internal"]
        )

    inc_df = fetch_incidents(
        run_id=sel_run,
        severity=sel_sev,
        status=sel_status,
        source_table=sel_table
    )

    total_inc = len(inc_df)
    open_inc = (inc_df["status"] == "OPEN").sum() if total_inc > 0 else 0
    crit_inc = (inc_df["severity"] == "CRITICAL").sum() if total_inc > 0 else 0
    alert_count = (inc_df["alert_sent"] == True).sum() if total_inc > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Incidents", total_inc)
    m2.metric("Open Incidents", open_inc)
    m3.metric("Critical Incidents", crit_inc)
    m4.metric("Alerts Dispatched", alert_count)

    st.divider()

    if inc_df.empty:
        st.success("✅ No incidents found matching the selected filter criteria.")
    else:
        st.subheader("Incident Registry")
        table_cols = [
            "incident_id", "severity", "status", "failure_type",
            "source_table", "check_id", "check_name", "affected_record_count",
            "detection_timestamp", "alert_sent"
        ]
        st.dataframe(
            inc_df[table_cols],
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.subheader("Incident Diagnostic Drilldown")

        for _, row in inc_df.iterrows():
            with st.expander(f"Incident #{row['incident_id']} - [{row['severity']}] {row['title']} (Run: {row['run_id'][:8]}...)"):
                d1, d2 = st.columns(2)
                with d1:
                    st.markdown(f"**Run ID:** `{row['run_id']}`")
                    st.markdown(f"**Severity:** {render_status_badge(row['severity'])}")
                    st.markdown(f"**Status:** {render_status_badge(row['status'])}")
                    st.markdown(f"**Primary Check:** `{row['check_id']}` ({row['check_name']})")
                    st.markdown(f"**Primary Table:** `{row['source_table']}`")
                with d2:
                    st.markdown(f"**Expected Value:** `{row['expected_value'] or 'N/A'}`")
                    st.markdown(f"**Observed Value:** `{row['observed_value'] or 'N/A'}`")
                    st.markdown(f"**Difference:** `{row['difference'] or 'N/A'}`")
                    st.markdown(f"**Affected Records:** `{row['affected_record_count']}`")
                    st.markdown(f"**Detection Time:** `{row['detection_timestamp']}`")
                    st.markdown(f"**Alert Sent:** `{row['alert_sent']}` ({row['alert_sent_at'] or 'N/A'})")

                st.markdown(f"**Description:**  \n{row['description']}")

                # Triggering Failures JSON
                st.markdown("**Complete Triggering Failures Payload:**")
                st.json(row["triggering_failures"])


# =============================================================================
# PAGE F: PIPELINE RUNS
# =============================================================================

def render_pipeline_runs():
    st.title("⏱️ Pipeline Runs & Execution History")
    st.markdown("Chronological audit log of all batch reliability pipeline executions.")

    runs_df = fetch_pipeline_runs()

    if runs_df.empty:
        st.info("No pipeline execution runs found.")
        return

    st.subheader("All Execution Runs")
    summary_cols = [
        "run_id", "status", "started_at", "completed_at",
        "duration_seconds", "source_filename"
    ]
    st.dataframe(runs_df[summary_cols], use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("Run Inspector & Lineage Drilldown")
    run_list = list(runs_df["run_id"].unique())
    selected_inspect_run = st.selectbox("Select Execution Run ID to Inspect", run_list)

    if selected_inspect_run:
        run_record = runs_df[runs_df["run_id"] == selected_inspect_run].iloc[0]

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Status", run_record["status"])
        r2.metric("Started", str(run_record["started_at"])[:19])
        r3.metric("Completed", str(run_record["completed_at"])[:19] if run_record["completed_at"] else "In Progress")
        r4.metric("Duration", f"{run_record['duration_seconds']}s" if run_record["duration_seconds"] else "N/A")

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown("**Raw Ingested Row Counts:**")
            st.json(run_record["raw_row_counts"] or {})

        with t_col2:
            st.markdown("**Warehouse Loading Counts (Trusted):**")
            trusted_counts = fetch_trusted_counts(selected_inspect_run)
            st.json(trusted_counts)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    st.sidebar.title("🛡️ Reliability Operations")
    st.sidebar.caption("DGCI&S E-Way Bill Movement Observability Platform")

    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.divider()

    selected_page = st.sidebar.radio("Navigate View", PAGES)

    st.sidebar.divider()
    st.sidebar.markdown(
        "**System Status:**  \n"
        "• Warehouse: `PostgreSQL`  \n"
        "• Mode: `Read-Only Audit`  \n"
        "• Orchestrator: `Apache Airflow`"
    )

    if selected_page == "📊 Overview":
        render_overview()
    elif selected_page == "🔍 Data Quality":
        render_data_quality()
    elif selected_page == "⚖️ Reconciliation":
        render_reconciliation()
    elif selected_page == "📈 Year-over-Year Statistics":
        render_statistics()
    elif selected_page == "🚨 Incidents":
        render_incidents()
    elif selected_page == "⏱️ Pipeline Runs":
        render_pipeline_runs()


if __name__ == "__main__":
    main()
