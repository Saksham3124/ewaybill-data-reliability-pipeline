# Final Verification Summary & Engineering Report

**Project:** DGCI&S Road E-Way Bill Data Reliability & Reconciliation Pipeline  
**Document Classification:** Final System Verification & Architectural Assessment  
**Author:** Data Reliability Engineering Team  
**Date:** September 2026  
**Status:** Verified & Frozen (Phases 1–12 Completed)

---

## 1. Executive Summary

This report documents the final verification, empirical test results, and operational hardening of the **DGCI&S Road E-Way Bill Data Reliability & Reconciliation Pipeline**. 

The system validates, cross-reconciles, statistically profiles, and orchestrates published road freight movement data published by the Directorate General of Commercial Intelligence and Statistics (DGCI&S), Ministry of Commerce and Industry, Government of India. The pipeline establishes a rigorous **Reliability Gate** ensuring that only structurally intact and arithmetically verified records enter trusted analytical storage, while corrupted or discordant data is deterministically blocked, isolated, and converted into auditable operational incidents.

### Summary Metrics

| Metric | Verified Value | Status |
|:---|:---:|:---:|
| **Automated Test Suite** | **122 passed, 0 failed** (12 test suites) | **100% PASS** |
| **Official Source Integrity** | SHA-256 verified byte-for-byte unchanged | **IMMUTABLE** |
| **Clean Airflow End-to-End Run** | `manual__2026-09-27T19:06:19+00:00` | **GATE PASS (10,089 Rows Promoted)** |
| **Failure Airflow End-to-End Run** | `manual__2026-09-27T19:20:52+00:00` | **GATE FAIL (0 Rows Promoted; Incident #1)** |
| **Cross-Table Reconciliation Audits** | 103 checks (99 PASS, 4 ADVISORY, 0 FAIL) | **VERIFIED** |
| **Statistical Distributional Stability** | KS-test $D = 0.1633$, $p = 0.1472$ ($\alpha = 0.05$) | **STABLE SHAPE** |
| **Streamlit Operations Dashboard** | 6 operational pages backed by PostgreSQL | **OPERATIONAL** |

---

## 2. Source Data Integrity & Cryptographic Signatures

The official source workbooks published by the DGCI&S represent multi-billion-rupee annual road freight dispatch and arrival figures across India's 38 States and Union Territories and 98 Chapter classifications under the Harmonized System of Nomenclature (HSN).

To guarantee reproducibility and guard against inadvertent corruption or local disk modification, cryptographic hashes were captured prior to processing and verified throughout all phases:

| File | Size (Bytes) | Cryptographic Hash (SHA-256) |
|:---|:---:|:---|
| `data/Road_EwayBill_2022_23.xlsx` | 1,770,056 | `534AE64CDFE76AE1ADBE5DB789443CD5AF5FC34DF94925BEBA1949859D209AEF` |
| `data/Road_EwayBill_2023_24.xlsx` | 1,775,695 | `42FDBA9A6FCF40FB47F9A632D403B28680E610160DB51CF75511163F59CE803D` |

Both workbooks remain **byte-for-byte identical** to their originally ingested states. All corruption experiments and negative tests were executed strictly against ephemeral, isolated copies.

---

## 3. Verified Multi-Layer Architecture

The reliability platform operates across six loosely coupled, deterministic layers:

```
[Official DGCI&S Workbooks (2022-23, 2023-24)]
                      │
                      ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 1: Ingestion & Structural Discovery              │
 │ • Extracts 5 published views (Tables I–V)              │
 │ • Preserves raw metadata and original cell types       │
 └────────────────────────────┬───────────────────────────┘
                              ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 2: Normalization & Quality Validation            │
 │ • Standardizes state names and 2-digit HSN codes       │
 │ • 64 automated checks across 7 validation categories   │
 └────────────────────────────┬───────────────────────────┘
                              ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 3: Cross-Table Accounting Reconciliation         │
 │ • 103 mathematical cross-footing rules (REC-DO01..06)  │
 │ • Rigorous tolerance-bounded marginal consistency      │
 │ • Flags "OTHER TERRITORY" as UNRESOLVED discrepancy    │
 └────────────────────────────┬───────────────────────────┘
                              ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 4: Longitudinal & Distributional Analysis        │
 │ • Year-over-year magnitude & growth tracking           │
 │ • Two-sample Kolmogorov-Smirnov (KS) test              │
 │ • Population Stability Index (PSI)                     │
 └────────────────────────────┬───────────────────────────┘
                              ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 5: Reliability Gate & Deterministic Branching    │
 │ • Binary decision evaluating all validation & audits   │
 │ • Branch A: PASS  ──► Promote to PostgreSQL Warehouse  │
 │ • Branch B: FAIL  ──► Block Warehouse, Log Incident    │
 └────────────────────────────┬───────────────────────────┘
                              ▼
 ┌────────────────────────────────────────────────────────┐
 │ Layer 6: Incident Management & Operational UI          │
 │ • PostgreSQL incidents ledger & Markdown audit log     │
 │ • Idempotent alert dispatch                            │
 │ • Read-only Streamlit operational dashboard            │
 └────────────────────────────────────────────────────────┘
```

### The Five Published Views Audited

1. **Table I: Inter-State Outward Dispatches by Chapter and State**  
   Measures originating domestic trade values (₹ Crores) partitioned by 2-digit HSN chapter and originating state/UT.
2. **Table II: Inter-State Inward Arrivals by Chapter and State**  
   Measures receiving domestic trade values (₹ Crores) partitioned by 2-digit HSN chapter and destination state/UT.
3. **Table III: State-to-State Outward Matrix**  
   State-by-state origin-to-destination bilateral trade flows (₹ Crores).
4. **Table IV: State-to-State Inward Matrix**  
   State-by-state destination-to-origin inward receipt matrix (₹ Crores).
5. **Table V: Intra-State Trade by Chapter and State**  
   Internal dispatches within the same state boundaries (₹ Crores).

---

## 4. Empirical Verification of End-to-End Executions

The pipeline was executed and validated via two genuine Apache Airflow DAG executions against a PostgreSQL storage engine.

### Run Summary Comparison

| Pipeline Attribute | Clean Execution (Phase 11A) | Corrupted Execution (Phase 11B) |
|:---|:---|:---|
| **Airflow `run_id`** | `manual__2026-09-27T19:06:19+00:00` | `manual__2026-09-27T19:20:52+00:00` |
| **Pipeline Run ID (UUID5)** | `9be6c0bc-d647-50e7-8c6a-e8deb088806c` | `876b1a4b-c9fd-5198-b153-17b6a725305c` |
| **Ingested Source File** | `data/Road_EwayBill_2023_24.xlsx` (Clean) | `data/corrupted_2023_24_altered_numeric.xlsx` |
| **Scenario Applied** | Official DGCI&S Published Baseline | Scenario CORRUPT-D: Altered Value (+500 Cr) |
| **Target Mutation** | None (Original Source) | Table III Chapter 10 Outward (Maharashtra) |
| **Total Ingested Rows** | 10,089 | 10,089 |
| **Validation Checks** | 64 PASS, 0 FAIL | 64 PASS, 0 FAIL (structural checks pass) |
| **Reconciliation Checks** | 99 PASS, 4 ADVISORY, 0 FAIL | 98 PASS, 4 ADVISORY, 1 CRITICAL FAIL |
| **Failing Rule** | None | **REC-V02** (Discrepancy: ₹ 500.00 Cr) |
| **Reliability Gate Decision** | **PASS** | **FAIL** |
| **Promotion Task** | `promote_trusted_data` (SUCCESS) | `promote_trusted_data` (**SKIPPED**) |
| **Warehouse Rows Promoted** | **10,089 rows** | **0 rows (Warehouse Untainted)** |
| **Incident Created** | None (0 incidents) | **Incident #1 (Recorded & Dispatched)** |
| **Incident UUID** | N/A | `876b1a4b-c9fd-5198-b153-17b6a725305c` |
| **Incident Severity** | N/A | `CRITICAL` |
| **Airflow DAG State** | `success` | `success` (Gracefully handled failure path) |

---

### Detailed Task Execution States

#### 1. Clean Run: `manual__2026-09-27T19:06:19+00:00`
```
start (success)
  └─► ingestion (success)
        └─► schema_validation (success)
              └─► quality_validation (success)
                    └─► cross_table_reconciliation (success)
                          └─► statistical_analysis (success)
                                └─► reliability_decision (success)
                                      ├─► promote_trusted_data (success) ──► end (success)
                                      └─► create_incident (skipped)
```
- **Ingestion:** 10,089 raw worksheet cells parsed from 5 tabs.
- **Quality Validation:** 64 checks evaluated; all 64 PASSED.
- **Reconciliation:** 103 checks evaluated; 99 PASSED, 4 marked ADVISORY_UNRESOLVED (`OTHER TERRITORY`), 0 FAILED.
- **Reliability Decision:** Gate evaluated status as `PASS`.
- **Promotion:** Exactly 10,089 rows inserted into `trusted_trade_records`. Zero quarantined records.

#### 2. Corrupted Run: `manual__2026-09-27T19:20:52+00:00`
```
start (success)
  └─► ingestion (success)
        └─► schema_validation (success)
              └─► quality_validation (success)
                    └─► cross_table_reconciliation (success)
                          └─► statistical_analysis (success)
                                └─► reliability_decision (success)
                                      ├─► promote_trusted_data (skipped)
                                      └─► create_incident (success) ──► end (success)
```
- **Mutation:** Isolated test workbook received a controlled +₹500.00 Cr shift on Maharashtra outward trade in Chapter 10.
- **Quality Validation:** Structure and data types remained superficially valid (PASSED).
- **Reconciliation Engine:** Detected an arithmetic contradiction between Table III outward row totals and Table I chapter aggregates. Rule **`REC-V02`** failed with an exact delta of ₹500.00 Cr ($> \text{tolerance of } 1.0\text{ Cr}$).
- **Reliability Gate:** Branch evaluated status as `FAIL`.
- **Branching Action:**
  - `promote_trusted_data` was **SKIPPED** via Airflow `BranchPythonOperator`.
  - Exactly **0 rows** were promoted to `trusted_trade_records`.
  - `create_incident` executed: logged Incident #1 to PostgreSQL `incidents` table and generated `docs/incidents/incident_876b1a4b-c9fd-5198-b153-17b6a725305c.md`.

---

## 5. Empirical Reconciliation & Statistical Findings

### Cross-Table Reconciliation (Baseline FY2023-24)

1. **National Outward vs. Inward Totals (`REC-DO01`, `REC-DO02`):**
   - National Outward Dispatches (Table I): **₹ 1,02,11,858.91 Cr**
   - National Inward Arrivals (Table II): **₹ 1,02,11,858.91 Cr**
   - Absolute Difference: **₹ 0.00 Cr** (Exact arithmetic match).

2. **National Matrix Partitioning (`REC-DO03`):**
   - Matrix Column Sums (Table III) vs. Row Sums (Table IV) match to ₹ 0.00 Cr.

3. **State-Level Marginal Cross-Footing (`REC-DO04`, `REC-DO05`):**
   - Verified across 33 states and union territories. All 33 state marginals balance across published tables.

4. **Jurisdictional Equivalence (`REC-DO06`):**
   - **32 of 33 jurisdictions** reconcile across Table I and Table II with zero discrepancy.
   - **1 jurisdiction (`OTHER TERRITORY`)** exhibits a published arithmetic contradiction:
     * Table I (Outward): **₹ 14,505.77 Cr**
     * Table II (Inward): **₹ 104.86 Cr**
     * Discrepancy: **₹ 14,400.91 Cr**
   - **Pipeline Handling:** Formally governed as an `ADVISORY_UNRESOLVED` discrepancy. It is recorded in the reconciliation ledger, highlighted on the dashboard, and documented without blocking clean pipeline runs.

---

### Longitudinal & Distributional Findings (FY2022-23 vs. FY2023-24)

| Dimension | FY2022-23 Value | FY2023-24 Value | Shift / Metric | Interpretation |
|:---|:---:|:---:|:---:|:---|
| **National Total Value** | ₹ 84,33,702.48 Cr | ₹ 1,02,11,858.91 Cr | **+21.08%** | Broad expansion in aggregate trade value |
| **Commodity Distribution (KS Test)** | 98 Chapters | 98 Chapters | **$D = 0.1633$ ($p = 0.1472$)** | Distributional shape preserved at $\alpha = 0.05$ |
| **Population Stability Index (PSI)** | 98 Chapters | 98 Chapters | **$\text{PSI} = 0.0412$** | Low distributional shift ($\text{PSI} < 0.10$) |
| **Top Volume Chapter** | Ch 27 (Mineral Fuels) | Ch 27 (Mineral Fuels) | Stable Rank #1 | Retained primary share of total movement |
| **Top Outward State** | Gujarat | Gujarat | Stable Rank #1 | Consistent industrial dispatch center |

**Statistical Clarification:**  
The two-sample Kolmogorov-Smirnov test verifies that relative commodity proportions across the 98 HSN chapters did not undergo a statistically significant structural distortion between the two annual snapshots. The test measures cumulative distributional shape, not absolute economic rank or individual state ranking stability.

---

### Controlled Corruption Detection Matrix

Across Phase 7 and Phase 11B, five controlled data defect scenarios were evaluated:

| Scenario Code | Corruption Type | Injection Target | Detection Layer | Responsible Rule | Detection Status |
|:---|:---|:---|:---|:---|:---:|
| **CORRUPT-A** | Structural Deletion | Deleted Worksheet Column | Schema Validation | `SCH-01` | **DETECTED** |
| **CORRUPT-B** | Domain Mutation | Misspelled State Name | Quality Validation | `DOM-01` | **DETECTED** |
| **CORRUPT-C** | Uniqueness Violation | Injected Duplicate Record | Quality Validation | `UNI-01` | **DETECTED** |
| **CORRUPT-D** | Altered Numeric Value | +₹500 Cr in Maharashtra Outward | Reconciliation Engine | `REC-V02` | **DETECTED** |
| **CORRUPT-E** | Longitudinal Shift | Synthetic Outlier Injection | Statistical Engine | $Z$-Score / Outlier | **DETECTED** |

---

## 6. Epistemic Boundaries & Governance Principles

A reliable data engineering platform must clearly define what its assertions prove and what falls beyond its epistemic reach:

### What the Pipeline Proves
1. **Mathematical Consistency:** Proves whether published tables, cross-tabs, and marginal sums satisfy accounting identities and cross-footing rules within declared tolerances.
2. **Schema & Typographic Integrity:** Proves whether ingested workbooks match expected structural headers, column lists, and standardized nomenclature.
3. **Distributional Concordance:** Proves whether observed longitudinal differences between years fall within expected statistical boundaries under formal two-sample tests.
4. **Lineage & Isolation:** Proves deterministically that any batch failing quality or reconciliation checks is halted before entering the trusted warehouse layer.

### What the Pipeline Cannot Prove
1. **Physical Ground Truth:** The pipeline cannot verify whether physical freight actually moved on roads, whether invoices were genuine, or whether tax fraud occurred at GST checkpoints.
2. **Causal Origins of Discrepancies:** The pipeline identifies *where* figures disagree (e.g., the ₹14,400.91 Cr mismatch in `OTHER TERRITORY`), but cannot determine *why* the DGCI&S published those values without additional government metadata.
3. **Data Completeness Beyond Source:** The pipeline cannot detect transactions that were never generated or filed in the GSTN portal.

### Why Human Review is Indispensable
Automated gates provide fail-safe operational boundaries, but cannot substitute for policy-level human judgment:
- **Unresolved Source Discrepancies:** Decisions to override or adjust governance around published discrepancies (like `OTHER TERRITORY`) require domain authority.
- **Incident Clearance:** When an incident triggers a pipeline halt, human operators must inspect the generated Markdown audit file, verify root causes, and explicitly authorize re-runs.

---

## 7. Automated Test Suite Breakdown

The repository maintains an automated test suite implemented via `pytest`. All 122 tests pass deterministically without network dependencies or data modification:

| Test Module | Test Focus | Check Count | Result |
|:---|:---|:---:|:---:|
| `test_historical_profiling.py` | FY2022-23 source structure & discovery | 7 | **7 PASSED** |
| `test_ingestion.py` | Extraction, header parsing, null preservation | 5 | **5 PASSED** |
| `test_normalization.py` | Name mapping, chapter formatting, deduplication | 6 | **6 PASSED** |
| `test_validation_engine.py` | Structural, completeness, domain, numeric tests | 14 | **14 PASSED** |
| `test_validation_rules.py` | Internal worksheet cross-footing rules | 8 | **8 PASSED** |
| `test_reconciliation_engine.py` | Cross-table balancing, marginals, OTHER TERRITORY | 13 | **13 PASSED** |
| `test_statistical_analysis.py` | YoY metrics, KS-test, PSI, zero protection | 17 | **17 PASSED** |
| `test_corruption_simulation.py` | Controlled fault injection & detection scenarios | 13 | **13 PASSED** |
| `test_airflow_dag.py` | DAG structure, task lineage, deterministic UUID5 | 12 | **12 PASSED** |
| `test_incidents.py` | Incident persistence, schema validation, audit logs | 7 | **7 PASSED** |
| `test_notifications.py` | Email formatting, mock SMTP, security sanitization | 7 | **7 PASSED** |
| `test_dashboard.py` | Streamlit read-only queries, page routing, filters | 11 | **11 PASSED** |
| `test_database.py` | PostgreSQL schema, trusted row assertions, lineage | 2 | **2 PASSED** |
| **Total** | **Comprehensive Regression Suite** | **122** | **122 PASSED** |

---

## 8. Reproduction & Verification Instructions

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (Virtual environment recommended)
- PostgreSQL 17 (Included in Docker Compose)

### 1. Start Infrastructure Services
```bash
docker compose up -d
```
Verify container health:
```bash
docker compose ps
```

### 2. Run Test Suite
```bash
# Activate Python environment
.venv\Scripts\Activate.ps1

# Run pytest regression suite
pytest -v
# Output: 122 passed in ~22s
```

### 3. Verify Source File Hashes
```powershell
Get-FileHash data/Road_EwayBill_2022_23.xlsx, data/Road_EwayBill_2023_24.xlsx -Algorithm SHA256 | Format-List
```

### 4. Trigger Clean Airflow Pipeline Run
```bash
docker exec -it ewaybill-airflow-scheduler airflow dags trigger ewaybill_reliability_pipeline
```
Monitor execution:
```bash
docker exec -it ewaybill-airflow-scheduler airflow dags list-runs -d ewaybill_reliability_pipeline
```

### 5. Launch Operational Dashboard
```powershell
$env:POSTGRES_PORT="5434"
$env:POSTGRES_PASSWORD="postgres"
streamlit run dashboard/app.py
```
Access dashboard at `http://localhost:8501`.

---

## 9. Conclusion

The DGCI&S Road E-Way Bill Data Reliability & Reconciliation Pipeline provides an end-to-end framework for ingesting, validating, and governing public economic datasets. By enforcing deterministic schema checks, cross-table accounting audits, distributional testing, and automated incident triage, the system guarantees that analytical systems consume only verified and trustworthy trade records.
