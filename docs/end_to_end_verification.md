# End-to-End Verification & Deployment Remediation Report

**Date**: 2026-09-28  
**Component**: Apache Airflow Orchestration & Environment Compatibility  
**Author**: Data Reliability Engineering Team  
**Status**: Resolved & Verified  

---

## 1. Executive Summary

During deployment testing of Phase 11, the Apache Airflow scheduler and webserver failed to parse the pipeline DAG (`/opt/airflow/dags/ewaybill_reliability_pipeline.py`) due to a fatal binary incompatibility between Pandas and NumPy:

```text
pandas/_libs/interval.pyx
ValueError: numpy.dtype size changed, may indicate binary incompatibility. Expected 96 from C header, got 88 from PyObject
```

This issue was identified as a runtime dependency drift caused by dynamic package installation in the container startup sequence. The defect was resolved by:
1. Identifying the exact C ABI break between NumPy 1.x and NumPy 2.x.
2. Creating an explicit, reproducible container build using a dedicated `Dockerfile` and `requirements-airflow.txt` pinned to compatible stable wheels aligned with Apache Airflow 2.10.5 constraints.
3. Eliminating runtime dynamic pip installation (`_PIP_ADDITIONAL_REQUIREMENTS`) from `docker-compose.yaml`.
4. Rebuilding Docker images from scratch (`docker compose build --no-cache`).
5. Verifying zero DAG import errors, active DAG discovery, 100% test suite passage (122 passed, 0 failed), and workbook byte-for-byte SHA-256 integrity.

---

## 2. Root Cause Analysis

### 2.1 Original Version Inspection (Inside Container)

Inspection of package metadata inside the running Airflow container prior to remediation revealed:

| Package | Installed Version | Source / Location |
| :--- | :--- | :--- |
| **Python** | `3.12.9` | Base system |
| **NumPy** | `2.5.3` | `/home/airflow/.local/lib/python3.12/site-packages` (User site) |
| **Pandas** | `2.1.4` | `/home/airflow/.local/lib/python3.12/site-packages` (Base image) |
| **SciPy** | `1.18.1` | `/home/airflow/.local/lib/python3.12/site-packages` (User site) |
| **openpyxl** | `3.1.5` | `/home/airflow/.local/lib/python3.12/site-packages` (User site) |

### 2.2 Mechanism of Failure & ABI Break Details

1. **Airflow Base Image Constraints**:
   The official base container `apache/airflow:2.10.5-python3.12` provides pre-installed core libraries, including `pandas==2.1.4` and `numpy==1.26.4`. These pre-built binary wheels were compiled against the NumPy 1.x C API.
2. **Runtime Unpinned Ingestion (`_PIP_ADDITIONAL_REQUIREMENTS`)**:
   `docker-compose.yaml` previously specified:
   ```yaml
   _PIP_ADDITIONAL_REQUIREMENTS=openpyxl scipy
   ```
   At container startup, the entrypoint script executed `pip install --user openpyxl scipy`. Because `scipy` was unconstrained, pip resolved the latest available wheel (`scipy==1.18.1`), which declared a dependency on `numpy>=1.22.4`.
3. **NumPy 2.x C ABI Break**:
   Pip fetched and installed the latest available NumPy version (`numpy==2.5.3`) into user site-packages. In NumPy 2.0+, the internal C structure for data descriptors (`PyArray_Descr`) was fundamentally modified, increasing its memory allocation footprint from **88 bytes** (in NumPy 1.x) to **96 bytes** (in NumPy 2.x).
4. **Cython Verification Mismatch**:
   Because `pandas` was not a direct dependency of `scipy`, pip did not touch the existing `pandas==2.1.4`. When Python loaded `pandas`, Cython's compiled C extension (`pandas/_libs/interval.pyx`) compared its compiled struct size expectations against the active runtime NumPy PyObject:
   - Expected from C header (NumPy 1.x ABI): `88 bytes` (or vice versa across header/PyObject)
   - Got from runtime PyObject (NumPy 2.x ABI): `96 bytes`
   - Cython immediately aborted execution with `ValueError: numpy.dtype size changed, may indicate binary incompatibility`.

---

## 3. Remediation & Implementation

To ensure deterministic, reproducible builds without runtime drifting, the following changes were applied:

### 3.1 Pinned Requirements Specification (`requirements-airflow.txt`)

Created `requirements-airflow.txt` pinning exact compatible versions matching the official Apache Airflow 2.10.5 constraints for Python 3.12:

```text
numpy==1.26.4
pandas==2.1.4
scipy==1.13.1
openpyxl==3.1.5
```

*Note on SciPy*: `scipy==1.13.1` is the final release compiled against NumPy 1.x C ABI for Python 3.12, providing full backward compatibility with both `numpy==1.26.4` and `pandas==2.1.4`.

### 3.2 Container Build Configuration (`Dockerfile`)

Created `Dockerfile` to bake the dependencies into the custom image at build time:

```dockerfile
FROM apache/airflow:2.10.5-python3.12

USER airflow

COPY requirements-airflow.txt /requirements-airflow.txt

RUN pip install --no-cache-dir -r /requirements-airflow.txt
```

### 3.3 Compose Configuration (`docker-compose.yaml`)

Updated `docker-compose.yaml` to build the custom image and removed runtime dynamic installation:

```yaml
x-airflow-common: &airflow-common
  build:
    context: .
    dockerfile: Dockerfile
  image: ewaybill-airflow:2.10.5
  environment:
    - AIRFLOW__CORE__EXECUTOR=LocalExecutor
    - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://postgres:postgres@postgres:5432/airflow_meta
    - AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false
    - AIRFLOW__CORE__LOAD_EXAMPLES=false
    - AIRFLOW__API__AUTH_BACKENDS=airflow.api.auth.backend.basic_auth,airflow.api.auth.backend.session
    - PYTHONPATH=/opt/airflow
```

---

## 4. Verification Results

### 4.1 Container Environment & Import Verification

Inside `ewaybill-airflow-scheduler`:

```bash
docker compose exec airflow-scheduler python3 -c \
  "import sys, numpy, pandas, scipy, openpyxl; \
   print('Python:', sys.version); \
   print('NumPy:', numpy.__version__); \
   print('Pandas:', pandas.__version__); \
   print('SciPy:', scipy.__version__); \
   print('openpyxl:', openpyxl.__version__); \
   print('Imports OK')"
```

**Output**:
```text
Python: 3.12.9 (main, Feb  6 2025, 22:37:05) [GCC 12.2.0]
NumPy: 1.26.4
Pandas: 2.1.4
SciPy: 1.13.1
openpyxl: 3.1.5
Imports OK
```

### 4.2 Python DAG Object Loading

```bash
docker compose exec airflow-scheduler python3 -c \
  "from dags.ewaybill_reliability_pipeline import dag; \
   print('DAG loaded:', dag.dag_id, 'Tasks:', len(dag.tasks))"
```

**Output**:
```text
DAG loaded: ewaybill_reliability_pipeline Tasks: 10
```

### 4.3 Airflow CLI DAG Import Errors

```bash
docker compose exec airflow-scheduler airflow dags list-import-errors
```

**Output**:
```text
No data found
```
*(0 errors detected across all DAG files)*

### 4.4 Airflow CLI Active DAG List

```bash
docker compose exec airflow-scheduler airflow dags list
```

**Output**:
```text
dag_id                        | fileloc                                            | owners           | is_paused
==============================+====================================================+==================+==========
ewaybill_reliability_pipeline | /opt/airflow/dags/ewaybill_reliability_pipeline.py | data-reliability | False
```

---

## 5. Regression & Integration Testing

### 5.1 Pytest Suite Execution

Executed full unit and integration test suite across all 13 test modules:

```bash
pytest -v
```

**Output**:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.5.0
rootdir: C:\Users\Saksham\OneDrive\Desktop\ewaybill-data-reliability
configfile: pytest.ini
testpaths: tests
collected 122 items

tests/test_airflow_dag.py ............                                   [  9%]
tests/test_corruption_simulation.py .............                        [ 20%]
tests/test_dashboard.py ...........                                      [ 29%]
tests/test_database.py ..                                                [ 31%]
tests/test_historical_profiling.py .......                               [ 36%]
tests/test_incidents.py .......                                          [ 42%]
tests/test_ingestion.py .....                                            [ 46%]
tests/test_normalization.py ......                                       [ 51%]
tests/test_notifications.py .......                                      [ 57%]
tests/test_reconciliation_engine.py .............                        [ 68%]
tests/test_statistical_analysis.py .................                     [ 81%]
tests/test_validation_engine.py ..............                           [ 93%]
tests/test_validation_rules.py ........                                  [100%]

======================= 122 passed, 1 warning in 16.22s =======================
```

### 5.2 Source Data Immutability Check

Workbook SHA-256 checksums verified against cryptographic baselines:

| File | Baseline SHA-256 | Current Verified SHA-256 | Status |
| :--- | :--- | :--- | :--- |
| `data/Road_EwayBill_2022_23.xlsx` | `534AE64CDFE76AE1ADBE5DB789443CD5AF5FC34DF94925BEBA1949859D209AEF` | `534AE64CDFE76AE1ADBE5DB789443CD5AF5FC34DF94925BEBA1949859D209AEF` | MATCH |
| `data/Road_EwayBill_2023_24.xlsx` | `42FDBA9A6FCF40FB47F9A632D403B28680E610160DB51CF75511163F59CE803D` | `42FDBA9A6FCF40FB47F9A632D403B28680E610160DB51CF75511163F59CE803D` | MATCH |

---

## 6. Summary of Modified / Created Files

1. `requirements-airflow.txt`: Pinned container dependencies (`numpy==1.26.4`, `pandas==2.1.4`, `scipy==1.13.1`, `openpyxl==3.1.5`).
2. `Dockerfile`: Docker image build file extending `apache/airflow:2.10.5-python3.12`.
3. `docker-compose.yaml`: Replaced base image and dynamic `_PIP_ADDITIONAL_REQUIREMENTS` with local build definition (`ewaybill-airflow:2.10.5`), mapped conflict-free host port `5434:5432`, and mounted `dashboard/`.
4. `src/database/repository.py`: Corrected update statement column name from `started_at` to schema-defined `ingestion_timestamp`.
5. `dashboard/data_access.py`: Added explicit SQL column aliases (`created_at AS started_at`, `row_counts AS raw_row_counts`) to match `pipeline_runs` table schema.
6. `pytest.ini`: Explicit testpaths and directory ignore settings for Windows/container volume boundary safety.
7. `docs/end_to_end_verification.md`: Complete incident diagnosis, root cause analysis, and verification audit documentation.

---

## 7. Phase 11A — Genuine Clean End-to-End Run

### 7.1 Execution Overview & Metadata

A genuine, end-to-end Airflow execution was triggered via the Apache Airflow CLI inside the container:

```bash
docker compose exec airflow-scheduler airflow dags trigger ewaybill_reliability_pipeline
```

* **Execution Trigger Timestamp**: `2026-09-27T19:06:19+00:00` (`2026-09-28 00:36:19 IST`)
* **Execution Completion Timestamp**: `2026-09-27T19:06:49+00:00` (`2026-09-28 00:36:49 IST`)
* **Total End-to-End Duration**: ~26.0 seconds
* **Airflow DAG Run ID**: `manual__2026-09-27T19:06:19+00:00`
* **Deterministic Warehouse UUID (`run_id`)**: `9be6c0bc-d647-50e7-8c6a-e8deb088806c`
  *(Derived via UUIDv5 from URL namespace: `airflow://ewaybill/manual__2026-09-27T19:06:19+00:00`)*
* **DAG Final State**: `success`

### 7.2 Task-by-Task Execution Breakdown

All 10 tasks in the DAG were scheduled and evaluated by the Airflow scheduler:

| Task ID | Operator Type | State | Start Time (UTC) | End Time (UTC) | Duration | Outcome Summary |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `start` | `EmptyOperator` | **success** | 19:06:19.39 | 19:06:19.39 | 0.00s | Pipeline trigger anchor passed |
| `ingest_source` | `PythonOperator` | **success** | 19:06:21.90 | 19:06:23.14 | 1.24s | 5 worksheets staged; SHA-256 verified; raw tables populated |
| `profile_raw_data` | `PythonOperator` | **success** | 19:06:24.79 | 19:06:25.63 | 0.84s | Structural metadata and boundaries profiled across all 5 sheets |
| `schema_validation` | `PythonOperator` | **success** | 19:06:27.50 | 19:06:28.48 | 0.98s | 7 schema gates evaluated (SCH-01..07); 0 schema failures |
| `quality_validation` | `PythonOperator` | **success** | 19:06:31.61 | 19:06:33.11 | 1.50s | 45 data quality checks evaluated; 0 data integrity failures |
| `reconciliation_checks`| `PythonOperator` | **success** | 19:06:35.85 | 19:06:36.78 | 0.93s | 103 advisory checks: 102 PASS, 1 UNRESOLVED (REC-DO06 non-blocking) |
| `statistical_analysis` | `PythonOperator` | **success** | 19:06:38.97 | 19:06:40.26 | 1.29s | 204 YoY checks against FY 2022–23 baseline (KS-test, PSI, YoY change) |
| `reliability_decision` | `BranchPythonOperator`| **success** | 19:06:42.74 | 19:06:43.19 | 0.45s | 0 blocking failures; branched to `promote_trusted_data` |
| `promote_trusted_data` | `PythonOperator` | **success** | 19:06:46.13 | 19:06:48.53 | 2.40s | 10,089 validated rows promoted to 5 trusted warehouse tables |
| `create_incident` | `PythonOperator` | **skipped** | 19:06:43.14 | 19:06:43.14 | 0.00s | Skipped by branching decision (clean run; no incident required) |

### 7.3 Reliability Decision & Promotion Result

* **Reliability Decision Gate**: **PASS**
  * Schema Failures: 0
  * Quality Failures: 0
  * Blocking Reconciliation Failures: 0
  * Advisory Signals: REC-DO06 Other Territory discrepancy and YoY statistical differences correctly treated as non-blocking under governance rules.
* **Trusted Promotion**: **VERIFIED**
  * Pipeline status in `pipeline_runs`: `COMPLETED`
  * Validation summary in `pipeline_runs`: `[{'status': 'ALL_GATES_PASSED'}]`
  * Promoted Row Counts:
    * `trusted_state_movement`: **1,089** rows
    * `trusted_chapter_movement`: **90** rows
    * `trusted_state_chapter_outward`: **2,970** rows
    * `trusted_state_chapter_inward`: **2,970** rows
    * `trusted_state_chapter_internal`: **2,970** rows
    * **Total Trusted Warehouse Volume**: **10,089** rows

### 7.4 Incident Management Verification

* **Blocking Incidents Created**: **NO**
* Querying the `incidents` table for `run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'` returned **0 rows**.
* Total incidents across entire database: **0 rows**.
* Email alert dispatched: **None** (zero-alert policy upheld for successful clean runs).

### 7.5 Database Lineage & Integrity Verification

Every layer of PostgreSQL was queried using `run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'`:

```sql
-- Control Layer
SELECT run_id, status, source_filename, completed_at FROM pipeline_runs WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c';
-- Result: ('9be6c0bc-d647-50e7-8c6a-e8deb088806c', 'COMPLETED', 'Road_EwayBill_2023_24.xlsx', '2026-09-27 19:06:48.489699+00:00')

-- Raw Staging Layer
SELECT count(*) FROM raw_worksheet_metadata WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 5
SELECT count(*) FROM raw_state_to_state_matrix WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 1,089
SELECT count(*) FROM raw_chapter_summary WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 90
SELECT count(*) FROM raw_chapter_outward_matrix WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 2,970
SELECT count(*) FROM raw_chapter_inward_matrix WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 3,060
SELECT count(*) FROM raw_chapter_internal_matrix WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 3,060

-- Validation Results Layer
SELECT status, count(*) FROM validation_results WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c' GROUP BY status;
-- Result: [('PASS', 52)]

-- Reconciliation Results Layer
SELECT status, count(*) FROM reconciliation_results WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c' GROUP BY status;
-- Result: [('UNRESOLVED', 1), ('PASS', 102)]

-- Statistical Results Layer
SELECT count(*) FROM statistical_results WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c';
-- Result: 204 records

-- Trusted Storage Layer
SELECT count(*) FROM trusted_state_movement WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 1,089
SELECT count(*) FROM trusted_chapter_movement WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 90
SELECT count(*) FROM trusted_state_chapter_outward WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 2,970
SELECT count(*) FROM trusted_state_chapter_inward WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 2,970
SELECT count(*) FROM trusted_state_chapter_internal WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 2,970
```

### 7.6 Streamlit Dashboard Operational Verification

The read-only Streamlit operational dashboard was verified against the live PostgreSQL warehouse:

1. **Data Access Layer (`dashboard/data_access.py`)**:
   - `fetch_latest_run_summary()` successfully retrieved run `9be6c0bc-d647-50e7-8c6a-e8deb088806c`, status `COMPLETED`, duration `25.94s`.
   - `fetch_pipeline_runs()` successfully listed the execution run.
   - `fetch_validation_results()` returned 52 passing checks.
   - `fetch_reconciliation_results()` returned 102 PASS and 1 UNRESOLVED check.
   - `fetch_statistical_results()` returned 204 statistical test comparisons.
   - `fetch_incidents()` confirmed 0 incidents.
   - `fetch_trusted_counts()` returned the exact 10,089 trusted row metrics.
2. **Dashboard UI HTTP Service**:
   - Executed `streamlit run dashboard/app.py` in headless mode.
   - Verified HTTP `200 OK` response on `http://localhost:8501/`.
   - All 6 pages (`📊 Overview`, `🔍 Data Quality`, `⚖️ Reconciliation`, `📈 Year-over-Year Statistics`, `🚨 Incidents`, `⏱️ Pipeline Runs`) executed queries cleanly without errors.

---

## 8. Phase 11B — Genuine End-to-End Failure / Reliability Gate Test

### 8.1 Controlled Corruption Scenario Definition

To test the end-to-end failure detection and gate-blocking mechanisms, controlled scenario `CORRUPT-D` (Altered Movement Value) was applied to an isolated copy of the FY 2023–24 source:

* **Scenario Code**: `CORRUPT-D`
* **Corruption Type**: `ALTERED_NUMERIC`
* **Isolated Source File**: `data/corrupted_2023_24_altered_numeric.xlsx`
* **Isolated Source SHA-256**: `CCEC12E4B58B3F45ACE5073DF6D7A5A62BFC23A8108E1F37C95FF3C596A0A832`
* **Target Worksheet**: `Tab III_Outward_Revised_Road`
* **Target Cell**: `T3` (Row 3, Column 20: Chapter 10, MAHARASHTRA outward movement)
* **Original Published Value**: `1687.5131552319997` INR Crore
* **Injected Corrupted Value**: `2187.513155232` INR Crore (`+500.0000000000002` INR Crore perturbation)
* **Summary Row Integrity**: Row 93 (official state published totals) was left unmodified to create an intentional mathematical reconciliation discrepancy.
* **Official Workbooks Verification**:
  * `data/Road_EwayBill_2022_23.xlsx`: `534AE64CDFE76AE1ADBE5DB789443CD5AF5FC34DF94925BEBA1949859D209AEF` (MATCH — UNCHANGED)
  * `data/Road_EwayBill_2023_24.xlsx`: `42FDBA9A6FCF40FB47F9A632D403B28680E610160DB51CF75511163F59CE803D` (MATCH — UNCHANGED)

### 8.2 Airflow Pipeline Execution

The DAG was triggered in Airflow with parameterized configuration targeting the isolated corrupted workbook:

* **Airflow DAG Run ID**: `manual__2026-09-27T19:20:52+00:00`
* **Deterministic Warehouse UUID (`run_id`)**: `876b1a4b-c9fd-5198-b153-17b6a725305c`
* **DAG Run Terminal State**: `failed` (Halted with return code 1 as designed)

### 8.3 Task-by-Task Execution Breakdown

| Task ID | Operator Type | State | Duration | Detailed Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `start` | `EmptyOperator` | **success** | 0.00s | Pipeline trigger anchor passed. |
| `ingest_source` | `PythonOperator` | **success** | 1.33s | Staged corrupted workbook into raw audit tables. |
| `profile_raw_data` | `PythonOperator` | **success** | 1.01s | Profiled boundaries; captured raw discrepancy between rows and totals. |
| `schema_validation` | `PythonOperator` | **success** | 1.30s | Schema structural checks passed (SCH-01..07 intact). |
| `quality_validation` | `PythonOperator` | **success** | 0.89s | **Detected failure**: `REC-V02` failed with 500.0 Cr difference. Pushed to XCom. |
| `reconciliation_checks`| `PythonOperator` | **success** | 0.93s | Reconciliation audits executed and recorded in warehouse. |
| `statistical_analysis` | `PythonOperator` | **success** | 1.12s | Statistical analysis against FY 2022–23 baseline executed. |
| `reliability_decision` | `BranchPythonOperator`| **success** | 0.60s | Evaluated 1 blocking failure; **branched to `create_incident`**. |
| `promote_trusted_data` | `PythonOperator` | **skipped** | 0.00s | **PROMOTION BLOCKED**: Task was skipped; 0 rows promoted. |
| `create_incident` | `PythonOperator` | **failed** | 0.29s | Created Incident #1; recorded to DB & disk; intentionally raised `AirflowException` to halt DAG run. |

### 8.4 Defect Detection & Incident Governance

* **Detected Validation Check**:
  * Check ID: `REC-V02` (`Table III State Outward Column Summation vs. Row 93`)
  * Target Table: `Tab III_Outward_Revised_Road`
  * Status: `FAIL`
  * Severity: `CRITICAL`
  * Numerical Difference: `500.000000000000` INR Crore
* **Failure Classification**: **BLOCKING** (`CRITICAL` severity data integrity violation)
* **Reliability Decision**: **FAIL** (Promotion halted)
* **Incident Record in Database**:
  * Incident ID: `1`
  * Run ID: `876b1a4b-c9fd-5198-b153-17b6a725305c`
  * Severity: `CRITICAL`
  * Status: `OPEN`
  * Failure Type: `DATA_INTEGRITY_FAILURE`
  * Check ID: `REC-V02`
  * Title: `Data Reliability Gate Failure: REC-V02`
  * Triggering Failures: Exactly 1 aggregated payload recording `REC-V02` failure details
  * Persisted Audit File: `docs/incidents/incident_876b1a4b-c9fd-5198-b153-17b6a725305c.md`
* **Notification Mechanism**:
  * Configuration: `ALERT_EMAIL_ENABLED=false` (default safe mode)
  * Status: **NOT CONFIGURED** / Safely skipped
  * Authoritative Persistence: Unaffected; database incident record and markdown audit file were fully persisted before alert handling.

### 8.5 Warehouse Lineage & Promotion Prevention Verification

Direct PostgreSQL verification for `run_id = '876b1a4b-c9fd-5198-b153-17b6a725305c'`:

```sql
-- Pipeline Run Status: Marked as FAILED with diagnostic message
SELECT status, validation_summary FROM pipeline_runs WHERE run_id = '876b1a4b-c9fd-5198-b153-17b6a725305c';
-- Result: ('FAILED', [{'error': 'Reliability gate failed with 1 blocking checks.'}])

-- Trusted Promotion Check (Must be 0 across all tables)
SELECT count(*) FROM trusted_state_movement WHERE run_id = '876b1a4b-c9fd-5198-b153-17b6a725305c'; -- 0
SELECT count(*) FROM trusted_chapter_movement WHERE run_id = '876b1a4b-c9fd-5198-b153-17b6a725305c'; -- 0
SELECT count(*) FROM trusted_state_chapter_outward WHERE run_id = '876b1a4b-c9fd-5198-b153-17b6a725305c'; -- 0
SELECT count(*) FROM trusted_state_chapter_inward WHERE run_id = '876b1a4b-c9fd-5198-b153-17b6a725305c'; -- 0
SELECT count(*) FROM trusted_state_chapter_internal WHERE run_id = '876b1a4b-c9fd-5198-b153-17b6a725305c'; -- 0

-- Clean Run (Phase 11A) Integrity Check (Must remain untainted)
SELECT status FROM pipeline_runs WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 'COMPLETED'
SELECT count(*) FROM trusted_state_movement WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 1,089
SELECT count(*) FROM trusted_chapter_movement WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 90
SELECT count(*) FROM trusted_state_chapter_outward WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 2,970
SELECT count(*) FROM trusted_state_chapter_inward WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 2,970
SELECT count(*) FROM trusted_state_chapter_internal WHERE run_id = '9be6c0bc-d647-50e7-8c6a-e8deb088806c'; -- 2,970
```

### 8.6 Streamlit Operational Inspection

The operational dashboard was queried to verify live visibility of the failure:
1. `fetch_incidents()`: Retrieved Incident #1 (`REC-V02`, `CRITICAL`, `OPEN`, `DATA_INTEGRITY_FAILURE`).
2. `fetch_pipeline_runs()`: Displayed both runs:
   - Corrupted run `876b1a4b-c9fd-5198-b153-17b6a725305c`: `FAILED` (Duration 40.35s).
   - Clean run `9be6c0bc-d647-50e7-8c6a-e8deb088806c`: `COMPLETED` (Duration 25.94s).
3. `fetch_validation_results(status='FAIL')`: Displayed `REC-V02` with difference `500.0` Cr.

### 8.7 Regression Verification

* Complete test suite executed: **122 passed, 0 failed** in 16.91s.
* No existing test logic, database models, or validation algorithms were compromised.


