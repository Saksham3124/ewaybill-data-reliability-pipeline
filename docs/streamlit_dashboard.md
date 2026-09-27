# Streamlit Reliability Dashboard Architecture & User Guide

**E-Way Bill Data Reliability & Reconciliation Platform**  
**Phase 10 Documentation**  
**Status:** Implemented & Verified (122/122 tests passing)

---

## 1. Dashboard Architecture

The Streamlit Reliability Dashboard provides a read-only operational interface designed specifically for data engineering, QA, and operations teams to monitor and audit the E-Way Bill batch reliability pipeline.

```
                      +---------------------------------------+
                      |           POSTGRESQL WAREHOUSE        |
                      |              (ewaybill_dw)            |
                      +---------------------------------------+
                                          |
                              [Strictly Read-Only Queries]
                                          |
                                          v
                      +---------------------------------------+
                      |        dashboard/data_access.py       |
                      |   - Parameterized SELECT statements   |
                      |   - Streamlit TTL Cache (@st.cache)   |
                      |   - Read-only session enforcement     |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |           dashboard/app.py            |
                      |   - 6 Operational Views / Pages       |
                      |   - Dynamic Multi-Attribute Filters   |
                      |   - Failure Diagnostics & JSON Payloads|
                      +---------------------------------------+
```

### Core Architectural Guarantees
1. **Separation of Presentation and Computation:**  
   The dashboard is strictly an observability layer. It never recalculates checks, never aggregates metrics independently, and never executes validation, reconciliation, or statistical formulas. All presented figures reflect pre-computed facts stored in the PostgreSQL warehouse.
2. **Absolute Read-Only Guarantee:**  
   The dashboard codebase contains zero write, update, or mutation SQL statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`). All database connections explicitly set `conn.set_session(readonly=True, autocommit=True)`.
3. **No Pipeline Mutation:**  
   The dashboard cannot create or resolve incidents, cannot retry or trigger Airflow DAG runs, and cannot dispatch alerts.

---

## 2. Dashboard Pages

The dashboard organizes operational visibility into six distinct views:

### A. 📊 Overview
- **Purpose:** High-level operational pulse for the latest pipeline run.
- **Components:**
  - Status indicator (`SUCCESS`, `FAILED`, `RUNNING`).
  - Core KPIs: checks passing ratio, reconciliation status, statistical shift count, open incidents count.
  - Latest run metadata: execution run ID, source workbook name, start/completion times, execution duration.
  - Warehouse promotion summary: count of normalized records loaded across the 5 trusted tables (`trusted_state_movement`, `trusted_chapter_movement`, `trusted_state_chapter_outward`, `trusted_state_chapter_inward`, `trusted_state_chapter_internal`).
  - Category breakdown matrix and recent pipeline history table.

### B. 🔍 Data Quality
- **Purpose:** Granular inspection of all 64 deterministic data-integrity check evaluations.
- **Components:**
  - KPI counters: Total Checks, Passed Checks, Failed Checks, Warnings.
  - Filters: Pipeline Run ID, Validation Category (`SCHEMA`, `COMPLETENESS`, `UNIQUENESS`, `DOMAIN`, `NUMERIC`, `STRUCTURAL`, `SOURCE_TOTAL`), Status (`PASS`, `FAIL`, `WARNING`), Source Table.
  - Category breakdown table displaying pass/fail counts by category.
  - Detailed audit table: `check_id`, `check_category`, `table_name`, `check_name`, `status`, `severity`, `expected_value`, `observed_value`, `difference`, `affected_records`, `message`.

### C. ⚖️ Reconciliation
- **Purpose:** Inspection of cross-table mathematical equilibrium and conservation audits (`REC-DO01` to `REC-DO06`, 102 audits).
- **Components:**
  - KPI counters: Total Audits, Resolved / Passed, Advisory Unresolved, Failed.
  - Filters: Run ID, Reconciliation Rule Code, Status (`PASS`, `UNRESOLVED`, `WARNING`, `FAIL`).
  - **Prominent Governance Banner:** Explicitly documents that `OTHER TERRITORY` under `REC-DO06` is recorded as an `UNRESOLVED non-blocking` finding, faithfully reflecting published DGCI&S figures without halting data promotion.
  - Detailed table: `rule_code`, `rule_category`, `source_tables`, `dimension`, `entity`, `expected_value`, `observed_value`, `absolute_difference`, `relative_difference`, `absolute_tolerance`, `status`, `severity`, `message`.

### D. 📈 Year-over-Year Statistics
- **Purpose:** Audit of macro-level distribution comparisons between FY 2022–23 and FY 2023–24 annual snapshots.
- **Components:**
  - **Mandatory Epistemic Guidance Banner:**
    > *"STATISTICALLY_DIFFERENT indicates an observed distributional difference under the configured analysis. It does not by itself indicate data corruption or pipeline failure."*
  - KPI counters: Evaluated Metrics, No Material Change, Statistically Different, Insufficient / N/A.
  - Filters: Run ID, Analytical Dimension, Test Method (`YOY_CHANGE`, `KS_TEST`, `PSI`, `CROSS_YEAR_OBSERVATION`), Status.
  - Detailed evaluation table: `comparison_year`, `reference_year`, `dimension`, `metric`, `test_method`, `sample_size_reference`, `sample_size_comparison`, `statistic`, `p_value`, `psi_value`, `status`, `interpretation`.
  - **Anti-Pattern Guard:** No state rankings, chapter rankings, or composite health scores are introduced.

### E. 🚨 Incidents
- **Purpose:** Registry of blocking data-integrity gate failures and operational triage status.
- **Components:**
  - KPI counters: Total Incidents, Open Incidents, Critical Incidents, Alerts Dispatched.
  - Filters: Severity (`CRITICAL`, `ERROR`, `WARNING`), Status (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`), Run ID, Source Table.
  - Summary registry table: `incident_id`, `severity`, `status`, `failure_type`, `source_table`, `check_id`, `check_name`, `affected_record_count`, `detection_timestamp`, `alert_sent`.
  - Diagnostic drill-down expanders (`st.expander`) displaying full incident metadata, failure descriptions, and the complete syntax-highlighted `triggering_failures` JSON payload.
  - **Read-Only Enforcement:** No buttons or controls exist to modify, acknowledge, or resolve incidents in this UI.

### F. ⏱️ Pipeline Runs
- **Purpose:** Chronological audit log of all batch executions.
- **Components:**
  - Full execution history table: `run_id`, `status`, `started_at`, `completed_at`, `duration_seconds`, `source_filename`.
  - Interactive Run Inspector: select any execution run to inspect raw ingested row counts (`raw_row_counts`) and golden warehouse promotion counts side-by-side.

---

## 3. Database Queries & Data Sources

All queries are executed through `dashboard.data_access` against the PostgreSQL database:

| Function | Source Table(s) | Operations | Caching |
| :--- | :--- | :--- | :--- |
| `fetch_pipeline_runs()` | `pipeline_runs` | `SELECT ... ORDER BY started_at DESC` | 60s TTL |
| `fetch_latest_run_summary()` | `pipeline_runs` | `SELECT ... ORDER BY started_at DESC LIMIT 1` | 60s TTL |
| `fetch_validation_results(...)` | `validation_results` | Parameterized `SELECT` with dynamic `WHERE` | 60s TTL |
| `fetch_reconciliation_results(...)`| `reconciliation_results`| Parameterized `SELECT` with dynamic `WHERE` | 60s TTL |
| `fetch_statistical_results(...)` | `statistical_results` | Parameterized `SELECT` with dynamic `WHERE` | 60s TTL |
| `fetch_incidents(...)` | `incidents` | Parameterized `SELECT` with dynamic `WHERE` | 60s TTL |
| `fetch_trusted_counts(run_id)` | `trusted_*` (5 tables) | `SELECT COUNT(*) WHERE run_id = %s` | 60s TTL |

---

## 4. Multi-Attribute Filtering

All operational pages provide responsive, server-side filtering:
- Dropdown filters default to `"ALL"`, with available values populated directly from the dataset.
- Filters generate parameterized SQL query clauses (`run_id = %s`, `check_category = %s`, etc.), ensuring efficient database retrieval without loading unnecessary rows into memory.

---

## 5. Refresh Behavior

- **Automated Caching:** Static and analytical query results are cached using Streamlit's `@st.cache_data(ttl=60)`. Queries remain fast and responsive during active analysis.
- **Manual Invalidation:** A prominent **`🔄 Refresh Data`** button in the sidebar triggers `st.cache_data.clear()` followed by `st.rerun()`, ensuring on-call operators can instantly observe new pipeline runs or newly recorded incidents.

---

## 6. Read-Only Guarantees

The dashboard strictly enforces read-only behavior through three layers of protection:
1. **Connection-Level Security:** Every connection explicitly invokes:
   ```python
   conn.set_session(readonly=True, autocommit=True)
   ```
2. **Codebase Static Invariant:** Static test audits (`test_read_only_sql_guarantee`) verify that no mutating SQL keywords exist in the dashboard source code.
3. **Absence of Mutation Callables:** No functions for creating, updating, or resolving incidents or dispatching Airflow runs exist in `dashboard/`.

---

## 7. Configuration

Connection parameters are read dynamically from environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `POSTGRES_HOST` | `127.0.0.1` | PostgreSQL database host |
| `POSTGRES_PORT` | `5433` | PostgreSQL port |
| `POSTGRES_DB` | `ewaybill_dw` | Warehouse database name |
| `POSTGRES_USER` | `postgres` | Database username |
| `POSTGRES_PASSWORD` | `Saksham@3124` | Database password |

Credentials are never hardcoded or displayed in UI components.

---

## 8. Local Startup Instructions

To launch the dashboard locally:

```bash
# 1. Activate project virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Launch Streamlit server
streamlit run dashboard/app.py
```

The application will be accessible in your web browser at:
```
http://localhost:8501
```

---

## 9. Security Considerations

- **Credential Masking:** Passwords and SMTP secrets are never output to UI cards, logs, or error popups.
- **Read-Only Session:** Even if an operator or malicious actor attempts to execute an ad-hoc write, PostgreSQL rejects it at the transaction level due to the `readonly=True` session attribute.
- **Parameterization:** All queries use `psycopg2` parameterized inputs (`%s`), preventing SQL injection.

---

## 10. Limitations

1. **Read-Only Scope:** Incident remediation (acknowledgment, resolution, adding resolution notes) must be performed via administrative database scripts or future back-office tooling.
2. **Local Session Scope:** Designed for local operational triage and team observability. Horizontal multi-tenant user authentication is not implemented.
