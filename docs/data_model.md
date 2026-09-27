# Database Data Model Documentation

**Target Database:** PostgreSQL 14+  
**Schema DDL File:** [`sql/schema.sql`](file:///c:/Users/Saksham/OneDrive/Desktop/ewaybill-data-reliability/sql/schema.sql)  
**Governance Phase:** Phase 3 — Data Foundation  
**Reporting Scope:** Government of India / DGCI&S Road E-Way Bill Movement Data (FY 2023–24)

---

## 1. Architectural Architecture & Layering

The database architecture employs a two-tier data lakehouse/warehouse design ensuring full auditability, reproducibility, and immutability:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Source Excel Workbook                           │
│                   data/Road_EwayBill_2023_24.xlsx                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Read-Only Ingestion (Loader)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        RAW AUDIT LAYER (raw_*)                         │
│  - Exact structural reproduction of Excel worksheets                    │
│  - Source row and column coordinate indexing                           │
│  - 100% preservation of source blanks/NULLs (Zero Imputation Prohibited)│
│  - Worksheet metadata & published totals recorded in raw_worksheet_meta│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Relational Normalization (Normalizer)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   TRUSTED NORMALIZED LAYER (trusted_*)                 │
│  - Third Normal Form (3NF) relational entities                         │
│  - Wide state matrices melted into entity-grain key-value rows         │
│  - Summary columns ('TOTAL') excluded from state grain                 │
│  - Natural composite keys enforced via UNIQUE constraints              │
│  - Source NULLs preserved (Calculations explicitly document 0-fill)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Table-by-Table Data Dictionary

---

### Layer 1: Control & Metadata Layer

#### Table: `pipeline_runs`
- **Purpose:** Tracks execution lifecycle, metadata, ingestion timestamps, and validation metrics for every pipeline execution.
- **Primary Key:** `run_id` (UUID)
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `run_id` | UUID | No | Unique surrogate run identifier generated via `gen_random_uuid()`. |
| `source_filename` | VARCHAR(255) | No | Basename of ingested source file (`Road_EwayBill_2023_24.xlsx`). |
| `source_filepath` | TEXT | No | Absolute canonical path to the ingested workbook on disk. |
| `ingestion_timestamp` | TIMESTAMPTZ | No | UTC timestamp when ingestion was initiated. |
| `status` | VARCHAR(50) | No | Lifecycle status (`'STARTED'`, `'COMPLETED'`, `'FAILED'`). |
| `row_counts` | JSONB | Yes | Key-value dictionary recording extracted rows per table. |
| `validation_summary` | JSONB | Yes | Summary of executed validation checks and pass/fail statuses. |
| `created_at` | TIMESTAMPTZ | No | System insertion timestamp. |
| `completed_at` | TIMESTAMPTZ | Yes | Pipeline termination timestamp. |

---

### Layer 2: Raw Audit Layer (`raw_*`)

#### Table: `raw_state_to_state_matrix`
- **Purpose:** Exact staging of Table I square matrix preserving sheet coordinates and cell nullability.
- **Source Worksheet:** `Tab I_Stat_to_Stat_Revised_Road` (Rows 4–36, Cols C–AI).
- **Primary Key:** `id` (BIGSERIAL)
- **Foreign Key:** `run_id` -> `pipeline_runs(run_id)`
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline run. |
| `from_state` | VARCHAR(100) | No | Column header state name (Origin entity). |
| `to_state` | VARCHAR(100) | No | Row label state name (Destination entity). |
| `movement_value` | NUMERIC(24, 12) | **Yes** | Cell monetary amount in INR Crore. **NULL preserved if blank.** |
| `source_row_index` | INT | No | 1-based Excel row number (4 to 36). |
| `source_col_index` | INT | No | 1-based Excel column number (3 to 35). |
| `created_at` | TIMESTAMPTZ | No | Staging timestamp. |

---

#### Table: `raw_chapter_summary`
- **Purpose:** Staging of Table II 2-digit HS Chapter commodity totals.
- **Source Worksheet:** `Tab II_Chap_Revised_Road` (Rows 3–92, Cols B, C, D).
- **Primary Key:** `id` (BIGSERIAL)
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline run. |
| `chapter_code` | VARCHAR(10) | No | 2-digit HS Chapter code (`'10'` through `'99'`). |
| `chapter_description` | TEXT | No | Official source commodity description. |
| `movement_value` | NUMERIC(24, 12) | **Yes** | Total chapter movement in INR Crore. |
| `source_row_index` | INT | No | 1-based Excel row number (3 to 92). |
| `created_at` | TIMESTAMPTZ | No | Staging timestamp. |

---

#### Table: `raw_chapter_outward_matrix`
- **Purpose:** Staging of Table III Chapter-by-State outward dispatches.
- **Source Worksheet:** `Tab III_Outward_Revised_Road` (Rows 3–92, Cols D–AJ).
- **Primary Key:** `id` (BIGSERIAL)
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline run. |
| `chapter_code` | VARCHAR(10) | No | 2-digit HS Chapter code (`'10'` through `'99'`). |
| `chapter_description` | TEXT | No | Official source commodity description. |
| `state` | VARCHAR(100) | No | State/UT dispatching outward freight. |
| `movement_value` | NUMERIC(24, 12) | **Yes** | Outward movement value in INR Crore. **NULL preserved.** |
| `source_row_index` | INT | No | 1-based Excel row number (3 to 92). |
| `created_at` | TIMESTAMPTZ | No | Staging timestamp. |

---

#### Table: `raw_chapter_inward_matrix`
- **Purpose:** Staging of Table IV Chapter-by-State inward receipts, including summary column.
- **Source Worksheet:** `Tab IV_Inward_Revised_Road` (Rows 3–92, Cols D–AK).
- **Primary Key:** `id` (BIGSERIAL)
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline run. |
| `chapter_code` | VARCHAR(10) | No | 2-digit HS Chapter code (`'10'` through `'99'`). |
| `chapter_description` | TEXT | No | Official source commodity description. |
| `state` | VARCHAR(100) | No | Receiving state name, or `'TOTAL'` for summary column. |
| `movement_value` | NUMERIC(24, 12) | **Yes** | Inward movement value in INR Crore. **NULL preserved.** |
| `is_summary_column` | BOOLEAN | No | `TRUE` if row corresponds to Column AK (`TOTAL`), else `FALSE`. |
| `source_row_index` | INT | No | 1-based Excel row number (3 to 92). |
| `created_at` | TIMESTAMPTZ | No | Staging timestamp. |

---

#### Table: `raw_chapter_internal_matrix`
- **Purpose:** Staging of Table V Chapter-by-State intra-state movements, including summary column.
- **Source Worksheet:** `Tab V_Internal_Revised_Road` (Rows 3–92, Cols D–AK).
- **Primary Key:** `id` (BIGSERIAL)
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline run. |
| `chapter_code` | VARCHAR(10) | No | 2-digit HS Chapter code (`'10'` through `'99'`). |
| `chapter_description` | TEXT | No | Official source commodity description. |
| `state` | VARCHAR(100) | No | State name, or `'TOTAL'` for summary column. |
| `movement_value` | NUMERIC(24, 12) | **Yes** | Internal movement value in INR Crore. **NULL preserved.** |
| `is_summary_column` | BOOLEAN | No | `TRUE` if row corresponds to Column AK (`TOTAL`), else `FALSE`. |
| `source_row_index` | INT | No | 1-based Excel row number (3 to 92). |
| `created_at` | TIMESTAMPTZ | No | Staging timestamp. |

---

#### Table: `raw_worksheet_metadata`
- **Purpose:** Captures sheet-level operational metadata, dimensions, null counts, and published summary totals (Row 93 / Cell AK93) for independent verification.
- **Primary Key:** `id` (BIGSERIAL)
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline run. |
| `worksheet_name` | VARCHAR(100) | No | Exact source worksheet name. |
| `title_text` | TEXT | Yes | Title block extracted from Row 1. |
| `data_start_row` | INT | No | 1-based starting row of tabular records. |
| `data_end_row` | INT | No | 1-based ending row of tabular records. |
| `row_count` | INT | No | Number of active tabular rows. |
| `column_count` | INT | No | Number of active tabular columns. |
| `null_cells_count` | INT | No | Total empty/null cells in data matrix. |
| `reported_total` | NUMERIC(24, 12) | Yes | Published scalar total from Row 93 / Cell AK93. |
| `reported_state_totals`| JSONB | Yes | Dictionary of published state totals from Row 93. |
| `created_at` | TIMESTAMPTZ | No | Metadata creation timestamp. |

---

### Layer 3: Normalized / Trusted Layer (`trusted_*`)

All normalized tables strictly implement the required entities specified in the governance prompt without inventing undocumented business fields.

---

#### Table: `trusted_state_movement`
- **Purpose:** Normalized relational representation of inter-state and intra-state movement between all origin and destination state pairs.
- **Source Worksheet:** `Tab I_Stat_to_Stat_Revised_Road`.
- **Primary Key:** `id` (BIGSERIAL)
- **Logical / Natural Key:** `(run_id, origin_state, destination_state)` — Enforced via `UNIQUE` constraint `uq_trusted_state_movement`.
- **Expected Row Count:** $33 \text{ origins} \times 33 \text{ destinations} = \mathbf{1,089\text{ rows}}$.
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline execution. |
| `origin_state` | VARCHAR(100) | No | State of dispatch (derived from Table I column headers). |
| `destination_state`| VARCHAR(100) | No | State of arrival (derived from Table I row headers). |
| `movement_value_inr_crore` | NUMERIC(24, 12) | **Yes** | Movement value in INR Crore. **NULL preserved if blank.** |
| `created_at` | TIMESTAMPTZ | No | Record insertion timestamp. |

- **NULL Handling:** Exactly 5 rows contain `NULL` (e.g. `Goa -> Manipur`, `Puducherry -> Mizoram`), reflecting routes where zero E-Way bills were generated.
- **Normalization Rule:** Unpivots the $33 \times 33$ wide matrix into long format.

---

#### Table: `trusted_chapter_movement`
- **Purpose:** Normalized summary of national road movement value categorized by 2-digit HS Chapter.
- **Source Worksheet:** `Tab II_Chap_Revised_Road`.
- **Primary Key:** `id` (BIGSERIAL)
- **Logical / Natural Key:** `(run_id, chapter_code)` — Enforced via `UNIQUE` constraint `uq_trusted_chapter_movement`.
- **Expected Row Count:** $\mathbf{90\text{ rows}}$ (Chapters 10 to 99).
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline execution. |
| `chapter_code` | VARCHAR(10) | No | 2-digit Harmonized System Chapter (`'10'` to `'99'`). |
| `chapter_description` | TEXT | No | Official commodity chapter narrative. |
| `movement_value_inr_crore` | NUMERIC(24, 12) | **Yes** | Total movement value in INR Crore. |
| `created_at` | TIMESTAMPTZ | No | Record insertion timestamp. |

- **NULL Handling:** Zero nulls exist in this table; all 90 chapters have valid positive values.
- **Normalization Rule:** 1:1 mapping from Table II data rows (Rows 3–92), excluding title (Row 1), header (Row 2), and total (Row 93).

---

#### Table: `trusted_state_chapter_outward`
- **Purpose:** Normalized representation of outward goods dispatches by commodity chapter and origin state.
- **Source Worksheet:** `Tab III_Outward_Revised_Road`.
- **Primary Key:** `id` (BIGSERIAL)
- **Logical / Natural Key:** `(run_id, chapter_code, state)` — Enforced via `UNIQUE` constraint `uq_trusted_state_chapter_outward`.
- **Expected Row Count:** $90 \text{ chapters} \times 33 \text{ states} = \mathbf{2,970\text{ rows}}$.
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline execution. |
| `chapter_code` | VARCHAR(10) | No | 2-digit HS Chapter code. |
| `chapter_description` | TEXT | No | Official commodity chapter narrative. |
| `state` | VARCHAR(100) | No | Dispatching origin state name. |
| `movement_value_inr_crore` | NUMERIC(24, 12) | **Yes** | Outward movement value in INR Crore. **NULL preserved.** |
| `created_at` | TIMESTAMPTZ | No | Record insertion timestamp. |

- **NULL Handling:** 108 records contain `NULL` (primarily in remote states and specialized chapters like Ch. 77, 43, 45).
- **Normalization Rule:** Unpivots the 33 state columns into rows. Excludes Row 93 summary totals.

---

#### Table: `trusted_state_chapter_inward`
- **Purpose:** Normalized representation of inward goods receipts by commodity chapter and destination state.
- **Source Worksheet:** `Tab IV_Inward_Revised_Road`.
- **Primary Key:** `id` (BIGSERIAL)
- **Logical / Natural Key:** `(run_id, chapter_code, state)` — Enforced via `UNIQUE` constraint `uq_trusted_state_chapter_inward`.
- **Expected Row Count:** $90 \text{ chapters} \times 33 \text{ states} = \mathbf{2,970\text{ rows}}$.
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline execution. |
| `chapter_code` | VARCHAR(10) | No | 2-digit HS Chapter code. |
| `chapter_description` | TEXT | No | Official commodity chapter narrative. |
| `state` | VARCHAR(100) | No | Receiving destination state name. |
| `movement_value_inr_crore` | NUMERIC(24, 12) | **Yes** | Inward movement value in INR Crore. **NULL preserved.** |
| `created_at` | TIMESTAMPTZ | No | Record insertion timestamp. |

- **NULL Handling:** 27 records contain `NULL`.
- **Normalization Rule:** Unpivots the 33 state columns into rows. **The `TOTAL` column (Col AK) is filtered out** during normalization because it represents a row-level aggregate, preserving strict atomicity.

---

#### Table: `trusted_state_chapter_internal`
- **Purpose:** Normalized representation of intra-state goods movements by commodity chapter and state.
- **Source Worksheet:** `Tab V_Internal_Revised_Road`.
- **Primary Key:** `id` (BIGSERIAL)
- **Logical / Natural Key:** `(run_id, chapter_code, state)` — Enforced via `UNIQUE` constraint `uq_trusted_state_chapter_internal`.
- **Expected Row Count:** $90 \text{ chapters} \times 33 \text{ states} = \mathbf{2,970\text{ rows}}$.
- **Columns:**

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :---: | :---: |
| `id` | BIGSERIAL | No | Auto-incrementing surrogate primary key. |
| `run_id` | UUID | No | References the pipeline execution. |
| `chapter_code` | VARCHAR(10) | No | 2-digit HS Chapter code. |
| `chapter_description` | TEXT | No | Official commodity chapter narrative. |
| `state` | VARCHAR(100) | No | State within which the internal movement occurred. |
| `movement_value_inr_crore` | NUMERIC(24, 12) | **Yes** | Internal movement value in INR Crore. **NULL preserved.** |
| `created_at` | TIMESTAMPTZ | No | Record insertion timestamp. |

- **NULL Handling:** 164 records contain `NULL`.
- **Normalization Rule:** Unpivots the 33 state columns into rows. **The `TOTAL` column (Col AK) is filtered out** during normalization to maintain entity-level atomicity.

---

## 3. Mandatory Governance & Quality Policies

### 3.1 Preserving Source Blanks/NULLs
1. **Raw and Trusted Layers:** Under Governance Constraint 2, source blanks/empty cells are stored strictly as SQL `NULL` (`None` in Python, `NaN` in pandas). **Global conversion of NULLs into `0.0` is strictly prohibited.**
2. **Calculation-Level Zero Imputation:** In mathematical validation checks (e.g. REC-V02, REC-V03) where summations require numerical operands, `NULL` values are handled using explicit local expressions:
   ```python
   # Explicit calculation-level zero treatment (source data remains unchanged)
   computed_sum = df[state_name].fillna(0.0).sum()
   ```
   Every such occurrence is explicitly documented at the calculation level.

### 3.2 The `OTHER TERRITORY` Boundary Policy
- Under Governance Constraint 7, `OTHER TERRITORY` is preserved exactly as published:
  - Table I Diagonal: **₹258,324.421758 Crore**
  - Table V Internal Total: **₹181,709.488219 Crore**
- The pipeline does not impute, rebalance, redistribute, or overwrite this ₹76,614.93 Crore difference.

---

## 4. Fields Deliberately NOT Created (Undocumented in Source)

In compliance with Governance Constraint 8 (*"Do not invent meanings for undocumented fields or relationships"*), the following fields were deliberately excluded from schema design:

1. **`hs_section` / `broad_commodity_sector`:**  
   The source dataset classifies goods solely by 2-digit HS chapter codes (`'10'` to `'99'`). No HS Section groupings (e.g. "Section I: Live Animals") are provided in the workbook.
2. **`consignor_gstin` / `consignee_gstin` / `taxpayer_type`:**  
   The workbook is an aggregate macroeconomic publication. Taxpayer identity fields do not exist.
3. **`vehicle_type` / `vehicle_number` / `distance_km` / `transit_time_days`:**  
   Physical logistics details are omitted from the source.
4. **`tax_rate` / `cgst_amount` / `sgst_amount` / `igst_amount` / `cess_amount`:**  
   The source reports only total taxable movement values. Tax liability breakdowns do not exist.
5. **`is_interstate` / `trade_balance_type`:**  
   Derived economic flags were not added to trusted tables to preserve source fidelity.
6. **`state_iso_code` / `census_code_2011` / `latitude` / `longitude`:**  
   External geospatial attributes were not injected into the core relational schema.
