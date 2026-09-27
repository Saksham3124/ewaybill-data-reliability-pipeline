# Data Reliability & Validation Report

**Pipeline Run ID:** `c9c51b72-9100-4d79-b607-65a3452b0e3e`  
**Execution Timestamp:** `2026-09-27 15:08:08 UTC`  
**Target Source:** `data/Road_EwayBill_2023_24.xlsx`  
**Validation Framework:** Phase 4 Automated Validation Engine  

---

## 1. Executive Summary

| Metric | Count | Percentage |
| :--- | :---: | :---: |
| **Total Checks Executed** | **64** | 100.0% |
| **Checks Passed** (`PASS`) | **64** | 100.0% |
| **Checks with Warnings** (`WARNING`) | **0** | 0.0% |
| **Checks Failed** (`FAIL`) | **0** | 0.0% |
| **Affected Tables** | **0** | - |
| **Total Affected Records** | **0** | - |

---

## 2. Checks by Validation Category

| Category | Total Checks | Passed | Warnings | Failed | Category Health |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **COMPLETENESS** | 7 | 7 | 0 | 0 | `HEALTHY` |
| **DOMAIN** | 9 | 9 | 0 | 0 | `HEALTHY` |
| **NUMERIC** | 20 | 20 | 0 | 0 | `HEALTHY` |
| **SCHEMA** | 12 | 12 | 0 | 0 | `HEALTHY` |
| **SOURCE_TOTAL** | 8 | 8 | 0 | 0 | `HEALTHY` |
| **STRUCTURAL** | 3 | 3 | 0 | 0 | `HEALTHY` |
| **UNIQUENESS** | 5 | 5 | 0 | 0 | `HEALTHY` |

---

## 3. Approved Source-Total Validations (REC-V01 through REC-V08)

These 8 intra-table mathematical checks represent verified balance assertions explicitly supported by source layout and totals:

| Rule ID | Check Name | Source Table | Status | Difference | Tolerance | Pass/Fail Rule |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **REC-V01** | Table II Chapter Row Summation vs. Row 93 Total | `Tab II_Chap_Revised_Road` | `PASS` | `0.00000000` | `0.0001` | Difference $\le$ Tolerance |
| **REC-V02** | Table III State Outward Column Summation vs. Row 93 | `Tab III_Outward_Revised_Road` | `PASS` | `0.00000000` | `0.0001` | Difference $\le$ Tolerance |
| **REC-V03** | Table IV State Inward Column Summation vs. Row 93 | `Tab IV_Inward_Revised_Road` | `PASS` | `0.00000000` | `0.0001` | Difference $\le$ Tolerance |
| **REC-V04** | Table IV Chapter Inward Row Summation vs. Column AK | `Tab IV_Inward_Revised_Road` | `PASS` | `0.00000000` | `0.0001` | Difference $\le$ Tolerance |
| **REC-V05** | Table IV Dual-Dimension Grand Total Cross-Foot | `Tab IV_Inward_Revised_Road` | `PASS` | `0.00000000` | `0.0001` | Difference $\le$ Tolerance |
| **REC-V06** | Table V State Internal Column Summation vs. Row 93 | `Tab V_Internal_Revised_Road` | `PASS` | `0.00000000` | `0.0001` | Difference $\le$ Tolerance |
| **REC-V07** | Table V Chapter Internal Row Summation vs. Column AK | `Tab V_Internal_Revised_Road` | `PASS` | `0.00000000` | `0.0001` | Difference $\le$ Tolerance |
| **REC-V08** | Table V Dual-Dimension Grand Total Cross-Foot | `Tab V_Internal_Revised_Road` | `PASS` | `0.00000000` | `0.0001` | Difference $\le$ Tolerance |

---

## 4. Comprehensive Validation Check Details

| Check ID | Category | Check Name | Target Table | Status | Severity | Message |
| :---: | :--- | :--- | :--- | :---: | :---: | :--- |
| **SCH-01** | SCHEMA | Expected Worksheets Presence | `raw_workbook` | `PASS` | `INFO` | All 5 expected sheets present. |
| **SCH-02-state_movement** | SCHEMA | Required Columns Presence | `state_movement` | `PASS` | `INFO` | All expected columns present in state_movement. |
| **SCH-03-state_movement** | SCHEMA | Undocumented Columns Detection | `state_movement` | `PASS` | `INFO` | No unexpected columns in state_movement. |
| **SCH-02-chapter_movement** | SCHEMA | Required Columns Presence | `chapter_movement` | `PASS` | `INFO` | All expected columns present in chapter_movement. |
| **SCH-03-chapter_movement** | SCHEMA | Undocumented Columns Detection | `chapter_movement` | `PASS` | `INFO` | No unexpected columns in chapter_movement. |
| **SCH-02-state_chapter_outward** | SCHEMA | Required Columns Presence | `state_chapter_outward` | `PASS` | `INFO` | All expected columns present in state_chapter_outward. |
| **SCH-03-state_chapter_outward** | SCHEMA | Undocumented Columns Detection | `state_chapter_outward` | `PASS` | `INFO` | No unexpected columns in state_chapter_outward. |
| **SCH-02-state_chapter_inward** | SCHEMA | Required Columns Presence | `state_chapter_inward` | `PASS` | `INFO` | All expected columns present in state_chapter_inward. |
| **SCH-03-state_chapter_inward** | SCHEMA | Undocumented Columns Detection | `state_chapter_inward` | `PASS` | `INFO` | No unexpected columns in state_chapter_inward. |
| **SCH-02-state_chapter_internal** | SCHEMA | Required Columns Presence | `state_chapter_internal` | `PASS` | `INFO` | All expected columns present in state_chapter_internal. |
| **SCH-03-state_chapter_internal** | SCHEMA | Undocumented Columns Detection | `state_chapter_internal` | `PASS` | `INFO` | No unexpected columns in state_chapter_internal. |
| **SCH-04-chapter-code-type** | SCHEMA | Chapter Code String Representation | `chapter_movement` | `PASS` | `INFO` | All chapter codes are stored as strings. |
| **CMP-01** | COMPLETENESS | state_movement Record Completeness | `state_movement` | `PASS` | `INFO` | Table state_movement has exactly 1089 records (expected 1089). |
| **CMP-02** | COMPLETENESS | chapter_movement Record Completeness | `chapter_movement` | `PASS` | `INFO` | Table chapter_movement has exactly 90 records (expected 90). |
| **CMP-03** | COMPLETENESS | state_chapter_outward Record Completeness | `state_chapter_outward` | `PASS` | `INFO` | Table state_chapter_outward has exactly 2970 records (expected 2970). |
| **CMP-04** | COMPLETENESS | state_chapter_inward Record Completeness | `state_chapter_inward` | `PASS` | `INFO` | Table state_chapter_inward has exactly 2970 records (expected 2970). |
| **CMP-05** | COMPLETENESS | state_chapter_internal Record Completeness | `state_chapter_internal` | `PASS` | `INFO` | Table state_chapter_internal has exactly 2970 records (expected 2970). |
| **CMP-06** | COMPLETENESS | Observed HS Chapter Set Completeness | `chapter_movement` | `PASS` | `INFO` | The source dataset contains HS Chapters 10–99. Chapters 01–09 are absent from the source. The reason for their absence is not documented in the workbook and is not asserted by this validation engine. |
| **CMP-07** | COMPLETENESS | Observed State Jurisdiction Completeness | `state_movement` | `PASS` | `INFO` | All 33 observed jurisdictions present. |
| **UNQ-01** | UNIQUENESS | state_movement Natural Key Uniqueness | `state_movement` | `PASS` | `INFO` | Logical key ['origin_state', 'destination_state'] is completely unique across 1089 rows. |
| **UNQ-02** | UNIQUENESS | chapter_movement Natural Key Uniqueness | `chapter_movement` | `PASS` | `INFO` | Logical key ['chapter_code'] is completely unique across 90 rows. |
| **UNQ-03** | UNIQUENESS | state_chapter_outward Natural Key Uniqueness | `state_chapter_outward` | `PASS` | `INFO` | Logical key ['chapter_code', 'state'] is completely unique across 2970 rows. |
| **UNQ-04** | UNIQUENESS | state_chapter_inward Natural Key Uniqueness | `state_chapter_inward` | `PASS` | `INFO` | Logical key ['chapter_code', 'state'] is completely unique across 2970 rows. |
| **UNQ-05** | UNIQUENESS | state_chapter_internal Natural Key Uniqueness | `state_chapter_internal` | `PASS` | `INFO` | Logical key ['chapter_code', 'state'] is completely unique across 2970 rows. |
| **DOM-01-state_movement** | DOMAIN | state_movement State Domain Conformance | `state_movement` | `PASS` | `INFO` | All states in state_movement conform to observed jurisdiction domain. |
| **DOM-01-state_chapter_outward** | DOMAIN | state_chapter_outward State Domain Conformance | `state_chapter_outward` | `PASS` | `INFO` | All states in state_chapter_outward conform to observed jurisdiction domain. |
| **DOM-01-state_chapter_inward** | DOMAIN | state_chapter_inward State Domain Conformance | `state_chapter_inward` | `PASS` | `INFO` | All states in state_chapter_inward conform to observed jurisdiction domain. |
| **DOM-01-state_chapter_internal** | DOMAIN | state_chapter_internal State Domain Conformance | `state_chapter_internal` | `PASS` | `INFO` | All states in state_chapter_internal conform to observed jurisdiction domain. |
| **DOM-02** | DOMAIN | Source Spelling Preservation (CHATTISGARH) | `state_movement` | `PASS` | `INFO` | Source spelling 'CHATTISGARH' correctly preserved without silent modification. |
| **DOM-03-chapter_movement** | DOMAIN | chapter_movement Chapter Code Format Conformance | `chapter_movement` | `PASS` | `INFO` | All chapter codes in chapter_movement are valid 2-digit HS chapters. |
| **DOM-03-state_chapter_outward** | DOMAIN | state_chapter_outward Chapter Code Format Conformance | `state_chapter_outward` | `PASS` | `INFO` | All chapter codes in state_chapter_outward are valid 2-digit HS chapters. |
| **DOM-03-state_chapter_inward** | DOMAIN | state_chapter_inward Chapter Code Format Conformance | `state_chapter_inward` | `PASS` | `INFO` | All chapter codes in state_chapter_inward are valid 2-digit HS chapters. |
| **DOM-03-state_chapter_internal** | DOMAIN | state_chapter_internal Chapter Code Format Conformance | `state_chapter_internal` | `PASS` | `INFO` | All chapter codes in state_chapter_internal are valid 2-digit HS chapters. |
| **NUM-01-state_movement** | NUMERIC | state_movement Non-Numeric Detection | `state_movement` | `PASS` | `INFO` | All movement values in state_movement are numeric or NULL. |
| **NUM-02-state_movement** | NUMERIC | state_movement Non-Negative Value Validation | `state_movement` | `PASS` | `INFO` | All movement values in state_movement are non-negative. |
| **NUM-03-state_movement** | NUMERIC | state_movement Infinite Value Detection | `state_movement` | `PASS` | `INFO` | Zero infinite values found in state_movement. |
| **NUM-05-state_movement** | NUMERIC | state_movement Source NULL Count Audit | `state_movement` | `PASS` | `INFO` | Exact expected NULL count (5) preserved in state_movement. |
| **NUM-01-chapter_movement** | NUMERIC | chapter_movement Non-Numeric Detection | `chapter_movement` | `PASS` | `INFO` | All movement values in chapter_movement are numeric or NULL. |
| **NUM-02-chapter_movement** | NUMERIC | chapter_movement Non-Negative Value Validation | `chapter_movement` | `PASS` | `INFO` | All movement values in chapter_movement are non-negative. |
| **NUM-03-chapter_movement** | NUMERIC | chapter_movement Infinite Value Detection | `chapter_movement` | `PASS` | `INFO` | Zero infinite values found in chapter_movement. |
| **NUM-05-chapter_movement** | NUMERIC | chapter_movement Source NULL Count Audit | `chapter_movement` | `PASS` | `INFO` | Exact expected NULL count (0) preserved in chapter_movement. |
| **NUM-01-state_chapter_outward** | NUMERIC | state_chapter_outward Non-Numeric Detection | `state_chapter_outward` | `PASS` | `INFO` | All movement values in state_chapter_outward are numeric or NULL. |
| **NUM-02-state_chapter_outward** | NUMERIC | state_chapter_outward Non-Negative Value Validation | `state_chapter_outward` | `PASS` | `INFO` | All movement values in state_chapter_outward are non-negative. |
| **NUM-03-state_chapter_outward** | NUMERIC | state_chapter_outward Infinite Value Detection | `state_chapter_outward` | `PASS` | `INFO` | Zero infinite values found in state_chapter_outward. |
| **NUM-05-state_chapter_outward** | NUMERIC | state_chapter_outward Source NULL Count Audit | `state_chapter_outward` | `PASS` | `INFO` | Exact expected NULL count (108) preserved in state_chapter_outward. |
| **NUM-01-state_chapter_inward** | NUMERIC | state_chapter_inward Non-Numeric Detection | `state_chapter_inward` | `PASS` | `INFO` | All movement values in state_chapter_inward are numeric or NULL. |
| **NUM-02-state_chapter_inward** | NUMERIC | state_chapter_inward Non-Negative Value Validation | `state_chapter_inward` | `PASS` | `INFO` | All movement values in state_chapter_inward are non-negative. |
| **NUM-03-state_chapter_inward** | NUMERIC | state_chapter_inward Infinite Value Detection | `state_chapter_inward` | `PASS` | `INFO` | Zero infinite values found in state_chapter_inward. |
| **NUM-05-state_chapter_inward** | NUMERIC | state_chapter_inward Source NULL Count Audit | `state_chapter_inward` | `PASS` | `INFO` | Exact expected NULL count (27) preserved in state_chapter_inward. |
| **NUM-01-state_chapter_internal** | NUMERIC | state_chapter_internal Non-Numeric Detection | `state_chapter_internal` | `PASS` | `INFO` | All movement values in state_chapter_internal are numeric or NULL. |
| **NUM-02-state_chapter_internal** | NUMERIC | state_chapter_internal Non-Negative Value Validation | `state_chapter_internal` | `PASS` | `INFO` | All movement values in state_chapter_internal are non-negative. |
| **NUM-03-state_chapter_internal** | NUMERIC | state_chapter_internal Infinite Value Detection | `state_chapter_internal` | `PASS` | `INFO` | Zero infinite values found in state_chapter_internal. |
| **NUM-05-state_chapter_internal** | NUMERIC | state_chapter_internal Source NULL Count Audit | `state_chapter_internal` | `PASS` | `INFO` | Exact expected NULL count (164) preserved in state_chapter_internal. |
| **STR-01** | STRUCTURAL | Raw to Normalized Transformation Conservation | `state_movement` | `PASS` | `INFO` | Source matrix (33x33) exactly normalized to 1089 records without leakage. |
| **STR-02-s4-total** | STRUCTURAL | Table IV Summary Column AK Presence | `Tab IV_Inward_Revised_Road` | `PASS` | `INFO` | Table IV summary column AK is present and populated. |
| **STR-03-s3-total-omission** | STRUCTURAL | Table III Omission of TOTAL Column Audit | `Tab III_Outward_Revised_Road` | `PASS` | `INFO` | Documented source discrepancy confirmed: Table III does not provide a TOTAL column. |
| **REC-V01** | SOURCE_TOTAL | Table II Chapter Row Summation vs. Row 93 Total | `Tab II_Chap_Revised_Road` | `PASS` | `INFO` | [DOCUMENTED BY OFFICIAL SOURCE] Sum of 90 chapter values strictly matches published national total (20,319,786.98 Crore). |
| **REC-V02** | SOURCE_TOTAL | Table III State Outward Column Summation vs. Row 93 | `Tab III_Outward_Revised_Road` | `PASS` | `INFO` | [DOCUMENTED BY OFFICIAL SOURCE] Chapter dispatches per state match published Row 93 totals. Null cells treated as 0.0 at calculation level. |
| **REC-V03** | SOURCE_TOTAL | Table IV State Inward Column Summation vs. Row 93 | `Tab IV_Inward_Revised_Road` | `PASS` | `INFO` | [DOCUMENTED BY OFFICIAL SOURCE] Chapter receipts per state match published Row 93 totals. Null cells treated as 0.0 at calculation level. |
| **REC-V04** | SOURCE_TOTAL | Table IV Chapter Inward Row Summation vs. Column AK | `Tab IV_Inward_Revised_Road` | `PASS` | `INFO` | [DOCUMENTED BY OFFICIAL SOURCE] Sum of state arrivals per chapter matches Column AK totals. Null cells treated as 0.0 at calculation level. |
| **REC-V05** | SOURCE_TOTAL | Table IV Dual-Dimension Grand Total Cross-Foot | `Tab IV_Inward_Revised_Road` | `PASS` | `INFO` | [DOCUMENTED BY OFFICIAL SOURCE] Sum of state totals matches published grand total in Cell AK93 (10,429,324.40 Crore). |
| **REC-V06** | SOURCE_TOTAL | Table V State Internal Column Summation vs. Row 93 | `Tab V_Internal_Revised_Road` | `PASS` | `INFO` | [DOCUMENTED BY OFFICIAL SOURCE] Internal chapter dispatches per state match published Row 93 totals. Null cells treated as 0.0 at calculation level. |
| **REC-V07** | SOURCE_TOTAL | Table V Chapter Internal Row Summation vs. Column AK | `Tab V_Internal_Revised_Road` | `PASS` | `INFO` | [DOCUMENTED BY OFFICIAL SOURCE] Sum of intra-state flows per chapter matches Column AK totals. Null cells treated as 0.0 at calculation level. |
| **REC-V08** | SOURCE_TOTAL | Table V Dual-Dimension Grand Total Cross-Foot | `Tab V_Internal_Revised_Road` | `PASS` | `INFO` | [DOCUMENTED BY OFFICIAL SOURCE] Sum of state internal totals matches published grand total in Cell AK93 (9,890,462.58 Crore). |

---

## 5. Architectural Status of Trusted Layer

> [!IMPORTANT]
> **ARCHITECTURAL GOVERNANCE RULE:**  
> In accordance with Phase 4 governance requirements, the `trusted_*` tables currently hold normalized/staging representations. They must **NOT** be certified as production-approved trusted data until complete cross-table reconciliation and methodology verification (Phase 5) have been completed.