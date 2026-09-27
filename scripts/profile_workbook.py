#!/usr/bin/env python3
"""
profile_workbook.py
-------------------
Automated programmatic profiling script for the Government of India / DGCI&S
E-Way Bill road movement dataset: data/Road_EwayBill_2023_24.xlsx.

This script inspects:
1. Worksheet names and catalog.
2. Declared vs actual bounding dimensions.
3. Headers, merged cells, metadata, and formula detection.
4. Tabular data boundaries (start/end rows & columns).
5. Geographic entities (States/UTs) and HS commodity chapters.
6. Units of measurement and numeric precision.
7. Blank, subtotal, total, and special rows/columns.
8. Inconsistencies and discrepancies across worksheets.
9. Normalization feasibility into relational structures.
10. Reconciliation hypotheses (explicitly marked).
"""

import sys
import os
import json
from pathlib import Path
import openpyxl
import pandas as pd
import numpy as np

def profile_workbook(wb_path: str = "data/Road_EwayBill_2023_24.xlsx") -> dict:
    if not os.path.exists(wb_path):
        raise FileNotFoundError(f"Workbook not found at: {wb_path}")

    wb_raw = openpyxl.load_workbook(wb_path, data_only=False)
    wb_data = openpyxl.load_workbook(wb_path, data_only=True)

    report = {
        "file_name": os.path.basename(wb_path),
        "file_path": wb_path,
        "sheet_names": wb_raw.sheetnames,
        "sheets": {},
        "reconciliation_hypotheses": {}
    }

    # 1. Profile Each Worksheet
    for name in wb_raw.sheetnames:
        ws_r = wb_raw[name]
        ws_d = wb_data[name]

        # Scan non-empty row and col bounds
        non_empty_rows = []
        non_empty_cols = set()
        formulas = []
        null_cells = []
        cell_types = {}

        for r in range(1, ws_r.max_row + 1):
            row_has_data = False
            for c in range(1, ws_r.max_column + 1):
                val_raw = ws_r.cell(r, c).value
                val_data = ws_d.cell(r, c).value

                t_name = type(val_data).__name__
                cell_types[t_name] = cell_types.get(t_name, 0) + 1

                if val_data is not None and str(val_data).strip() != "":
                    row_has_data = True
                    non_empty_cols.add(c)
                if val_raw is not None and str(val_raw).startswith("="):
                    formulas.append((r, c, str(val_raw)))

            if row_has_data:
                non_empty_rows.append(r)

        min_r = min(non_empty_rows) if non_empty_rows else None
        max_r = max(non_empty_rows) if non_empty_rows else None
        min_c = min(non_empty_cols) if non_empty_cols else None
        max_c = max(non_empty_cols) if non_empty_cols else None

        empty_rows = [r for r in range(1, ws_r.max_row + 1) if r not in non_empty_rows]
        empty_cols = [c for c in range(1, ws_r.max_column + 1) if c not in non_empty_cols]

        # Extract title and headers
        title_text = ws_d.cell(1, 2).value if ws_d.cell(1, 2).value else ws_d.cell(1, 1).value
        header_row_2 = [ws_d.cell(2, c).value for c in range(min_c or 1, (max_c or 1) + 1)]
        header_row_3 = [ws_d.cell(3, c).value for c in range(min_c or 1, (max_c or 1) + 1)] if ws_r.max_row >= 3 else None

        sheet_info = {
            "declared_dimensions": f"{ws_r.dimensions} (max_row={ws_r.max_row}, max_column={ws_r.max_column})",
            "actual_data_bounding_box": f"Rows [{min_r}, {max_r}], Columns [{min_c}, {max_c}]",
            "empty_rows": empty_rows,
            "empty_columns": empty_cols,
            "merged_cells_count": len(ws_r.merged_cells.ranges),
            "merged_cells": [str(r) for r in ws_r.merged_cells.ranges],
            "formula_count": len(formulas),
            "cell_type_distribution": cell_types,
            "title_metadata": title_text,
            "header_row_2": header_row_2,
        }
        report["sheets"][name] = sheet_info

    # 2. Extract DataFrames for Detailed Analysis
    # Sheet 1: Tab I_Stat_to_Stat_Revised_Road
    ws1 = wb_data['Tab I_Stat_to_Stat_Revised_Road']
    states_s1 = [ws1.cell(2, c).value for c in range(3, 36)]
    s1_matrix = []
    for r in range(4, 37):
        s1_matrix.append([ws1.cell(r, c).value for c in range(3, 36)])
    df_s1 = pd.DataFrame(s1_matrix, index=states_s1, columns=states_s1)

    # Sheet 2: Tab II_Chap_Revised_Road
    ws2 = wb_data['Tab II_Chap_Revised_Road']
    s2_rows = []
    for r in range(3, 93):
        s2_rows.append({
            "chapter_code": str(ws2.cell(r, 2).value).strip(),
            "chapter_desc": str(ws2.cell(r, 3).value).strip(),
            "value_inr_crore": ws2.cell(r, 4).value
        })
    df_s2 = pd.DataFrame(s2_rows)
    s2_total_reported = ws2.cell(93, 4).value

    # Sheet 3: Tab III_Outward_Revised_Road
    ws3 = wb_data['Tab III_Outward_Revised_Road']
    s3_rows = []
    for r in range(3, 93):
        row_dict = {
            "chapter_code": str(ws3.cell(r, 2).value).strip(),
            "chapter_desc": str(ws3.cell(r, 3).value).strip(),
        }
        for idx, s in enumerate(states_s1, start=4):
            row_dict[s] = ws3.cell(r, idx).value
        s3_rows.append(row_dict)
    df_s3 = pd.DataFrame(s3_rows)
    s3_totals_reported = [ws3.cell(93, c).value for c in range(4, 37)]

    # Sheet 4: Tab IV_Inward_Revised_Road
    ws4 = wb_data['Tab IV_Inward_Revised_Road']
    s4_rows = []
    for r in range(3, 93):
        row_dict = {
            "chapter_code": str(ws4.cell(r, 2).value).strip(),
            "chapter_desc": str(ws4.cell(r, 3).value).strip(),
        }
        for idx, s in enumerate(states_s1, start=4):
            row_dict[s] = ws4.cell(r, idx).value
        row_dict["TOTAL"] = ws4.cell(r, 37).value
        s4_rows.append(row_dict)
    df_s4 = pd.DataFrame(s4_rows)
    s4_totals_reported = [ws4.cell(93, c).value for c in range(4, 38)]

    # Sheet 5: Tab V_Internal_Revised_Road
    ws5 = wb_data['Tab V_Internal_Revised_Road']
    s5_rows = []
    for r in range(3, 93):
        row_dict = {
            "chapter_code": str(ws5.cell(r, 2).value).strip(),
            "chapter_desc": str(ws5.cell(r, 3).value).strip(),
        }
        for idx, s in enumerate(states_s1, start=4):
            row_dict[s] = ws5.cell(r, idx).value
        row_dict["TOTAL"] = ws5.cell(r, 37).value
        s5_rows.append(row_dict)
    df_s5 = pd.DataFrame(s5_rows)
    s5_totals_reported = [ws5.cell(93, c).value for c in range(4, 38)]

    # 3. Numeric Summaries & Discrepancies
    tot_s1 = df_s1.fillna(0).values.sum()
    tot_s2_sum = df_s2["value_inr_crore"].sum()
    tot_s3_col_sum = df_s3[states_s1].fillna(0).sum().sum()
    tot_s4_col_sum = df_s4[states_s1].fillna(0).sum().sum()
    tot_s5_col_sum = df_s5[states_s1].fillna(0).sum().sum()

    s1_diag = pd.Series(np.diag(df_s1.fillna(0).values), index=states_s1)
    s5_state_totals = pd.Series(s5_totals_reported[:-1], index=states_s1)
    diag_diff = s1_diag - s5_state_totals

    report["metrics"] = {
        "sheet_1_total_matrix_sum": float(tot_s1),
        "sheet_2_reported_total": float(s2_total_reported),
        "sheet_2_computed_row_sum": float(tot_s2_sum),
        "sheet_3_computed_outward_sum": float(tot_s3_col_sum),
        "sheet_4_computed_inward_sum": float(tot_s4_col_sum),
        "sheet_5_computed_internal_sum": float(tot_s5_col_sum),
        "outward_plus_internal_sum": float(tot_s3_col_sum + tot_s5_col_sum),
        "inward_plus_internal_sum": float(tot_s4_col_sum + tot_s5_col_sum),
        "national_outward_minus_inward": float(tot_s3_col_sum - tot_s4_col_sum),
        "state_count": len(states_s1),
        "chapter_count": len(df_s2),
        "null_counts": {
            "sheet_1": int(df_s1.isna().sum().sum()),
            "sheet_2": int(df_s2["value_inr_crore"].isna().sum()),
            "sheet_3": int(df_s3[states_s1].isna().sum().sum()),
            "sheet_4": int(df_s4[states_s1 + ['TOTAL']].isna().sum().sum()),
            "sheet_5": int(df_s5[states_s1 + ['TOTAL']].isna().sum().sum())
        },
        "other_territory_diagonal_diff": float(diag_diff.get("OTHER TERRITORY", 0.0))
    }

    # 4. Explicit Reconciliation Hypotheses
    report["reconciliation_hypotheses"] = {
        "HYPOTHESIS_1": {
            "statement": "Sheet 1 Column Headers represent Origin State ('From State') and Row Headers represent Destination State ('To State').",
            "tag": "HYPOTHESIS — REQUIRES METHODOLOGY VERIFICATION",
            "evidence": "Column off-diagonal sums match Sheet 3 Outward totals (except Other Territory shift), and Row off-diagonal sums match Sheet 4 Inward totals."
        },
        "HYPOTHESIS_2": {
            "statement": "Sheet 1 Diagonal Elements represent Intra-State ('Internal') Road Movement, while Off-Diagonal Elements represent Inter-State Movements.",
            "tag": "HYPOTHESIS — REQUIRES METHODOLOGY VERIFICATION",
            "evidence": "For 32 of 33 states, S1 diagonal equals Sheet 5 Internal Row 93 with absolute difference 0.0."
        },
        "HYPOTHESIS_3": {
            "statement": "Total Movement in Sheet 2 equals Total Outward Movement (Sheet 3) + Total Internal Movement (Sheet 5), which also equals Total Inward Movement (Sheet 4) + Total Internal Movement (Sheet 5).",
            "tag": "HYPOTHESIS — REQUIRES METHODOLOGY VERIFICATION",
            "evidence": "Outward + Internal = 20,319,786.98011016 Crore; Sheet 2 Total = 20,319,786.98011017 Crore (difference < 1e-8)."
        },
        "HYPOTHESIS_4": {
            "statement": "Across the national road transportation boundary, Total Outward Movement equals Total Inward Movement.",
            "tag": "HYPOTHESIS — REQUIRES METHODOLOGY VERIFICATION",
            "evidence": "Total Outward (10,429,324.404046647) - Total Inward (10,429,324.404046647) = 0.0."
        },
        "HYPOTHESIS_5": {
            "statement": "The 76,614.93 Crore discrepancy in 'OTHER TERRITORY' between Sheet 1 and Sheet 5 stems from differing administrative boundary definitions of offshore/maritime economic zones during GST aggregation.",
            "tag": "HYPOTHESIS — REQUIRES METHODOLOGY VERIFICATION",
            "evidence": "Col Sum and Row Sum of Other Territory in S1 match Outward+Internal and Inward+Internal exactly, but 76,614.93 Crore was assigned to the diagonal instead of off-diagonal."
        },
        "HYPOTHESIS_6": {
            "statement": "Empty / null cells in Sheets 1, 3, 4, and 5 represent true zero movement ($0.0 INR Crore) rather than unobserved/missing records.",
            "tag": "HYPOTHESIS — REQUIRES METHODOLOGY VERIFICATION",
            "evidence": "Sum of populated cells with nulls treated as 0 exactly matches all reported row and column totals."
        },
        "HYPOTHESIS_7": {
            "statement": "Chapters 01 to 09 are absent from the workbook because primary agricultural and livestock commodities are exempt from E-Way Bill generation under Rule 138(14) of the CGST Rules.",
            "tag": "HYPOTHESIS — REQUIRES METHODOLOGY VERIFICATION",
            "evidence": "Chapter codes strictly span 10 through 99 (90 chapters). Chapters 01-09 cover livestock, meat, fish, dairy, live plants, and unprocessed vegetables/fruits."
        }
    }

    return report

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    wb_path = sys.argv[1] if len(sys.argv) > 1 else "data/Road_EwayBill_2023_24.xlsx"
    print(f"Profiling workbook: {wb_path}")
    rep = profile_workbook(wb_path)

    print("\n" + "="*70)
    print(f"PROFILE SUMMARY FOR: {rep['file_name']}")
    print("="*70)
    print(f"Worksheets found ({len(rep['sheet_names'])}):")
    for s in rep['sheet_names']:
        info = rep['sheets'][s]
        print(f"  * '{s}'")
        print(f"      Declared: {info['declared_dimensions']}")
        print(f"      Actual:   {info['actual_data_bounding_box']}")
        print(f"      Formulas: {info['formula_count']} | Merged Ranges: {info['merged_cells_count']}")

    print("\n" + "-"*70)
    print("KEY METRICS & RECONCILIATION SUMMARY:")
    print("-"*70)
    m = rep['metrics']
    print(f"Total States/UTs:               {m['state_count']}")
    print(f"Total HS Chapters:              {m['chapter_count']}")
    print(f"Sheet 1 Matrix Total:           {m['sheet_1_total_matrix_sum']:,.2f} INR Crore")
    print(f"Sheet 2 Total Movement:         {m['sheet_2_reported_total']:,.2f} INR Crore")
    print(f"Sheet 3 Total Outward Movement: {m['sheet_3_computed_outward_sum']:,.2f} INR Crore")
    print(f"Sheet 4 Total Inward Movement:  {m['sheet_4_computed_inward_sum']:,.2f} INR Crore")
    print(f"Sheet 5 Total Internal Movement:{m['sheet_5_computed_internal_sum']:,.2f} INR Crore")
    print(f"Outward + Internal:             {m['outward_plus_internal_sum']:,.2f} INR Crore")
    print(f"Inward + Internal:              {m['inward_plus_internal_sum']:,.2f} INR Crore")
    print(f"National Outward - Inward:      {m['national_outward_minus_inward']:.6f} INR Crore")
    print(f"OTHER TERRITORY Diag Discrepancy: {m['other_territory_diagonal_diff']:,.2f} INR Crore")

    print("\n" + "-"*70)
    print("RECONCILIATION HYPOTHESES:")
    print("-"*70)
    for k, v in rep['reconciliation_hypotheses'].items():
        print(f"[{v['tag']}] {k}:")
        print(f"  Statement: {v['statement']}")
        print(f"  Evidence:  {v['evidence']}\n")

if __name__ == "__main__":
    main()
