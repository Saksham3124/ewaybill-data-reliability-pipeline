# DGCI&S Road E-Way Bill Data Reliability & Reconciliation Pipeline

An end-to-end, statistically grounded data reliability and cross-table reconciliation engine for the Directorate General of Commercial Intelligence and Statistics (DGCI&S) inter-state and intra-state goods movement datasets (FY 2022–23 and FY 2023–24).

Repository: [https://github.com/Saksham3124/ewaybill-data-reliability-pipeline](https://github.com/Saksham3124/ewaybill-data-reliability-pipeline)

---

## 1. Problem Statement & Why Data Reliability Matters

Government and regulatory trade statistics are frequently published as complex, multi-worksheet Excel workbooks designed for human visual inspection rather than automated data pipelines. These workbooks feature:
* Multi-level headers and merged title cells
* Formatted summary rows with embedded arithmetic checksums
* State-level naming variations and spelling shifts across financial years
* Asymmetric matrix dimensions (e.g., 33 states in outward dispatches vs. 34 jurisdictions in inward/internal tables)
* Unstated cross-table mathematical dependencies

Traditional ETL pipelines often assume clean, tabular inputs and load unverified data directly into reporting warehouses. When upstream source formatting drifts, data values are corrupted, or trade balances diverge, downstream analytical models and policy decisions are contaminated silently.

This project implements an **active data reliability framework**: every workbook must pass strict structural validation, mathematical cross-table reconciliation, and year-over-year statistical divergence checks before records are permitted to enter trusted analytical storage.

---

## 2. Architecture & Pipeline Sequence

```
                                SOURCE WORKBOOKS
                     data/Road_EwayBill_2022_23.xlsx (Baseline)
                     data/Road_EwayBill_2023_24.xlsx (Current)
                                        │
                                        ▼
                     1. INGESTION & RAW STAGING (PostgreSQL)
                        - Cryptographic SHA-256 verification
                        - Exact cell preservation into raw_* tables
                        - Canonical state & chapter normalization
                                        │
                                        ▼
                     2. DATA RELIABILITY EVALUATION ENGINE
                        ├── Schema Validation (SCH-01..07)
                        ├── Quality Validation (Completeness, Uniqueness, Domain, Numeric)
                        ├── Source Total Summation Checks (REC-V01..08)
                        ├── Cross-Table Reconciliation (REC-DO01..06)
                        └── Year-over-Year Statistical Analysis (KS Test, PSI, YoY Deltas)
                                        │
                                        ▼
                              3. RELIABILITY GATE
                                        │
                   ┌────────────────────┴────────────────────┐
                   ▼                                         ▼
            [ALL GATES PASS]                        [BLOCKING FAILURE]
                   │                                         │
                   ▼                                         ▼
      4a. TRUSTED PROMOTION                    4b. INCIDENT MANAGEMENT
      - Load into 5 trusted tables             - Authoritative PostgreSQL record
      - Mark run as COMPLETED                  - Generate docs/incidents/ report
      - Promote 10,089 golden rows             - Attempt SMTP email alert
                                               - Halt promotion; mark FAILED
                                        │
                                        ▼
                      5. STREAMLIT OPERATIONAL DASHBOARD
                         - Purely read-only inspection (SELECT only)
                         - 6 operational monitoring pages
```

---

## 3. Data Source & Five Published Views

Data is published by the **Directorate General of Commercial Intelligence and Statistics (DGCI&S)**, Ministry of Commerce and Industry, Government of India:

| Published View | Sheet Name | Dimensions | Description |
| :--- | :--- | :---: | :--- |
| **Table I** | `Tab I_Stat_to_Stat_Revised_Road` | 33 × 33 | State-to-State inter-state road movement matrix (1,089 pairs). |
| **Table II** | `Tab II_Chap_Revised_Road` | 90 × 4 | 2-digit HS Chapter summary (Chapters 10–99). |
| **Table III** | `Tab III_Outward_Revised_Road` | 90 × 33 | Chapter × State outward dispatches (2,970 state-chapter combinations). |
| **Table IV** | `Tab IV_Inward_Revised_Road` | 90 × 34 | Chapter × State inward arrivals (3,060 combinations; includes `OTHER TERRITORY`). |
| **Table V** | `Tab V_Internal_Revised_Road` | 90 × 34 | Chapter × State intra-state movements (3,060 combinations; includes `OTHER TERRITORY`). |

---

## 4. Reliability Layers & Methodology

### 4.1 Validation Layer
Evaluates deterministic structural and data-integrity rules:
* **Schema Conformance (SCH-01..07)**: Header labels, column counts, data boundaries, and sheet presence.
* **Completeness & Uniqueness**: Verification of exact expected row counts and composite key uniqueness `(chapter_code, state)`.
* **Domain Validation**: Verification of ISO state names and 2-digit HS chapter codes (10–99).
* **Numeric Boundaries**: Non-negativity, float precision preservation, and explicit NULL preservation.
* **Source Reported Totals (REC-V01..08)**: Verification of matrix row/column cell sums against published Row 93 and Table II published totals.

### 4.2 Cross-Table Reconciliation Layer
Audits 6 mathematical relationships observed across independent worksheets:
* **REC-DO01**: National outward total (Table III) equals national inward total (Table IV).
* **REC-DO02**: State-to-State grand total (Table I) equals national outward total (Table III).
* **REC-DO03**: National trade balance partitioning (Outward + Internal = Inward + Internal).
* **REC-DO04**: State column marginal sums in Table I match state outward column sums in Table III.
* **REC-DO05**: State row marginal sums in Table I match state inward column sums in Table IV.
* **REC-DO06**: State-level trade balance across all 33 states and union territories.
  * **Advisory Status**: 32 of 33 jurisdictions pass within numerical tolerance. `OTHER TERRITORY` exhibits an unresolved cross-table discrepancy in the published source data. Under pipeline governance, this is classified as advisory **`UNRESOLVED`** and does not block data promotion.

### 4.3 Year-over-Year Statistical Analysis
Compares annual snapshots between **FY 2022–23** (reference baseline) and **FY 2023–24** (current comparison snapshot):
* **Kolmogorov-Smirnov (KS) Two-Sample Test**: Evaluates whether annual distributions share the same continuous shape ($\alpha = 0.05$).
* **Population Stability Index (PSI)**: Quantifies bucketed shift magnitude across annual snapshots ($< 0.10$ stable, $0.10–0.25$ moderate, $\ge 0.25$ significant).
* **Year-over-Year Change Deltas**: State and chapter-level growth percentages with zero-denominator safeguards.
* **Epistemic Boundary**: `STATISTICALLY_DIFFERENT` is treated as an informational signal reflecting annual magnitude differences, **not** as a pipeline failure or proof of data corruption.

### 4.4 Reliability Gate & Promotion Semantics
The `reliability_decision` branch enforces strict gate semantics:
* **Blocking Failures**: Any failure in schema conformance, completeness, uniqueness, domain format, numeric integrity, or source-total verification immediately triggers `reliability_decision = FAIL`. Promotion is halted, and an incident is raised.
* **Advisory Signals**: Cross-table `UNRESOLVED` conditions (e.g., `OTHER TERRITORY`) and statistical divergence (`STATISTICALLY_DIFFERENT`) are non-blocking.
* **Trusted Promotion**: Only clean runs reaching `reliability_decision = PASS` promote staging records into the 5 trusted warehouse tables (`trusted_*`).

---

## 5. Verified End-to-End Results

The following figures represent measured, empirical results from the verified end-to-end Airflow execution runs (documented in `docs/end_to_end_verification.md`), not theoretical claims:

| Metric / Evaluation Area | Clean Run Result (Phase 11A) | Corrupted Run Result (Phase 11B) |
| :--- | :---: | :---: |
| **Airflow DAG Tasks Scheduled** | 10 tasks executed | 10 tasks evaluated |
| **Airflow Run State** | `success` | `failed` (halted at gate) |
| **Validation Evaluations** | **52 / 52 PASS** | 1 detected failure (`REC-V02`) |
| **Reconciliation Evaluations** | **102 PASS, 1 UNRESOLVED** | 102 PASS, 1 UNRESOLVED |
| **Statistical Test Results** | **204 comparisons evaluated** | 204 comparisons evaluated |
| **Reliability Gate Decision** | **`PASS`** | **`FAIL`** |
| **Promotion to Trusted Warehouse** | **10,089 rows promoted** | **0 rows promoted (BLOCKED)** |
| **Incident Created in PostgreSQL** | **0 incidents** | **1 incident created (`CRITICAL`)** |
| **Clean Warehouse Lineage Preserved** | Verified | Verified (10,089 clean rows untainted) |
| **Full Pytest Test Suite** | **122 / 122 passed (100%)** | **122 / 122 passed (100%)** |
| **Official Source SHA-256 Hashes** | Unchanged | Unchanged (Byte-for-byte identical) |

---

## 6. Controlled Corruption Testing

The pipeline's detection capabilities were validated across 7 controlled synthetic corruption scenarios on isolated copies:

| Scenario Code | Corruption Injected | Detection Layer | Resulting Gate Action |
| :--- | :--- | :--- | :---: |
| **`CORRUPT-A`** | Missing single record `(Chapter 10, Maharashtra)` | Completeness (`CMP-03`) | **BLOCKED** |
| **`CORRUPT-B`** | Duplicate record appended | Uniqueness (`UNQ-03`) | **BLOCKED** |
| **`CORRUPT-C`** | Invalid chapter code `'999'` injected | Domain (`DOM-03`) | **BLOCKED** |
| **`CORRUPT-D`** | $+500.0$ Cr added to Maharashtra Chapter 10 | Source-Total (`REC-V02`) | **BLOCKED** |
| **`CORRUPT-E`** | State column `BIHAR` removed from Table III | Completeness & Reconciliation | **BLOCKED** |
| **`CORRUPT-F`** | Numeric float replaced with string text | Numeric (`NUM-01`) | **BLOCKED** |
| **`CORRUPT-G`** | Synthetic $100\times$ volume distribution multiplier | Statistical (KS Test & PSI) | **ADVISORY** (Non-blocking) |

*Controlled corruptions evaluate specific single-point defect detection; they do not imply universal detection of all possible corrupted inputs.*

---

## 7. Streamlit Operational Dashboard

The platform includes a read-only Streamlit dashboard (`dashboard/app.py`) for operational inspection:
* **📊 Overview**: High-level execution status, core KPIs, quality ratios, and recent run history.
* **🔍 Data Quality**: Interactive filtering across all validation checks by run, table, category, and severity.
* **⚖️ Reconciliation**: Matrix of cross-table mathematical audits with clear explanation of `OTHER TERRITORY`.
* **📈 Year-over-Year Statistics**: Distributional comparisons (KS test, PSI, YoY changes) with epistemic guidance.
* **🚨 Incidents**: Authoritative incident registry with full JSON diagnostic payloads.
* **⏱️ Pipeline Runs**: Chronological run history and raw vs. trusted row count lineage.

*Read-Only Guarantee: All dashboard queries execute with `readonly=True` connection sessions; the UI cannot mutate database state, alter incidents, or trigger DAG runs.*

---

## 8. Quickstart & Reproducibility Guide

### Prerequisites
* Python 3.12+
* Docker & Docker Compose
* Git

### Step 1: Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/Saksham3124/ewaybill-data-reliability-pipeline.git
cd ewaybill-data-reliability-pipeline

python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Start PostgreSQL & Airflow via Docker Compose
```bash
# Build custom Airflow image with pinned compatible dependencies
docker compose build --no-cache

# Start PostgreSQL and Airflow services in detached mode
docker compose up -d
```

### Step 3: Run Full Test Suite
```bash
pytest -v
# Output: 122 passed in ~16s
```

### Step 4: Trigger Clean Airflow Pipeline Run
```bash
docker compose exec airflow-scheduler airflow dags trigger ewaybill_reliability_pipeline
```

### Step 5: Launch Streamlit Dashboard
```bash
# Configure connection parameters (port 5434 maps to container database on host)
$env:POSTGRES_PORT="5434"
$env:POSTGRES_PASSWORD="postgres"

streamlit run dashboard/app.py
```
Open `http://localhost:8501` in your browser.

---

## 9. Project Structure

```
ewaybill-data-reliability/
├── dags/
│   └── ewaybill_reliability_pipeline.py  # Airflow DAG definition (10 tasks)
├── dashboard/
│   ├── app.py                            # Streamlit dashboard application (6 pages)
│   └── data_access.py                    # Read-only parameterized database queries
├── data/
│   ├── Road_EwayBill_2022_23.xlsx        # Baseline financial year workbook
│   └── Road_EwayBill_2023_24.xlsx        # Current financial year workbook
├── docs/
│   ├── end_to_end_verification.md        # Comprehensive Phases 11A and 11B verification logs
│   ├── final_verification_summary.md     # Architectural audit & limitation summary
│   ├── corruption_detection_report.md    # Controlled corruption evaluation report
│   ├── corruption_test_spec.md           # Controlled corruption test specifications
│   ├── incident_management.md            # Incident lifecycle & alerting design
│   ├── reconciliation_report.md          # Cross-table reconciliation findings
│   ├── statistical_analysis_report.md    # Year-over-year statistical report
│   └── validation_report.md              # Rule-by-rule data validation catalogue
├── sql/
│   ├── schema.sql                        # PostgreSQL warehouse DDL (raw, control, results, trusted)
│   └── init_multiple_dbs.sh              # Multi-database container initialization
├── src/
│   ├── corruption/                       # Controlled corruption scenario generators
│   ├── database/                         # Connection manager & data repository
│   ├── incidents/                        # Authoritative incident creation & file logging
│   ├── ingestion/                        # Openpyxl workbook loaders & hash checkers
│   ├── notifications/                    # Email alerting service
│   ├── reconciliation/                   # Cross-table mathematical engine
│   ├── statistics/                       # KS-test, PSI, and YoY comparison engine
│   ├── transformation/                   # Canonical jurisdiction & chapter normalizers
│   └── validation/                       # Schema and data quality validation engine
├── tests/                                # 13 test modules covering all pipeline components
├── Dockerfile                            # Reproducible Airflow container build
├── docker-compose.yaml                   # Airflow, PostgreSQL 17, and volume setup
├── requirements.txt                      # Python environment dependencies
└── requirements-airflow.txt              # Pinned binary-compatible container dependencies
```

---

## 10. Analytical Disclaimers & Known Limitations

1. **Annual Snapshot Discontinuity**: The comparison between FY 2022–23 and FY 2023–24 is an analysis of two annual static snapshots. It does not represent continuous, streaming data drift monitoring.
2. **Epistemic Limits of Statistical Significance**: Rejection of the null hypothesis in a Kolmogorov-Smirnov test indicates distributional shape divergence across annual snapshots; it does not constitute proof of data defect, pipeline error, or economic causality.
3. **`OTHER TERRITORY` Discrepancy**: The numerical divergence in `OTHER TERRITORY` reflects an unstated accounting methodology in the primary DGCI&S source data. It is audited as an advisory condition, not an operational bug.
4. **Scope of Corruption Testing**: The 7 controlled corruption scenarios demonstrate the sensitivity of the specific configured validation rules; they do not constitute universal defect detection guarantees.
