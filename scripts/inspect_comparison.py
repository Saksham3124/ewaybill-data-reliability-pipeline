import json

with open('scratch_historical_comparison.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

p22 = data['prof_2022_23']
p24 = data['prof_2023_24']

print('=== FILE STATS ===')
print('2022-23:', p22['filename'], f"({p22['size_bytes']} bytes, SHA256: {p22['sha256']})")
print('2023-24:', p24['filename'], f"({p24['size_bytes']} bytes, SHA256: {p24['sha256']})")

print('\n=== SHEET NAMES ===')
print('2022-23:', p22['sheet_names'])
print('2023-24:', p24['sheet_names'])
print('Identical Sheet Names?:', p22['sheet_names'] == p24['sheet_names'])

print('\n=== SHEET DIMENSIONS & BOUNDS ===')
for s in p22['sheet_names']:
    s22 = p22['sheets'][s]
    s24 = p24['sheets'][s]
    print(f'[{s}]')
    print(f'  2022-23: Declared: {s22["declared_max_row"]}x{s22["declared_max_col"]}, Active: rows {s22["active_min_row"]}-{s22["active_max_row"]} cols {s22["active_min_col"]}-{s22["active_max_col"]}')
    print(f'  2023-24: Declared: {s24["declared_max_row"]}x{s24["declared_max_col"]}, Active: rows {s24["active_min_row"]}-{s24["active_max_row"]} cols {s24["active_min_col"]}-{s24["active_max_col"]}')
    print(f'  Title 22-23: {s22["title_cell_A1"]}')
    print(f'  Title 23-24: {s24["title_cell_A1"]}')
    print(f'  Merged Ranges count: 22-23={s22["merged_cells_count"]}, 23-24={s24["merged_cells_count"]}')
    print(f'  Formula count: 22-23={s22["formula_count"]}, 23-24={s24["formula_count"]}')

print('\n=== STATE / JURISDICTION COMPARISON ===')
s1_22 = p22['sheets']['Tab I_Stat_to_Stat_Revised_Road']['entity_details']
s1_24 = p24['sheets']['Tab I_Stat_to_Stat_Revised_Road']['entity_details']
print('2022-23 Origin States count:', len(s1_22['origin_states']))
print('2023-24 Origin States count:', len(s1_24['origin_states']))
print('Origin States Identical?:', s1_22['origin_states'] == s1_24['origin_states'])
print('Dest States Identical?:', s1_22['dest_states'] == s1_24['dest_states'])
print('Origin == Dest in 22-23?:', s1_22['origin_states'] == s1_22['dest_states'])

# Check state names in Sheet 3, 4, 5
for sheet in ['Tab III_Outward_Revised_Road', 'Tab IV_Inward_Revised_Road', 'Tab V_Internal_Revised_Road']:
    st22 = p22['sheets'][sheet]['entity_details']['states']
    st24 = p24['sheets'][sheet]['entity_details']['states']
    print(f'{sheet} States Identical?: {st22 == st24}')

print('\n=== CHAPTER COMPARISON ===')
c22 = p22['sheets']['Tab II_Chap_Revised_Road']['entity_details']
c24 = p24['sheets']['Tab II_Chap_Revised_Road']['entity_details']
print('2022-23 Chapters count:', c22['chapters_count'])
print('2023-24 Chapters count:', c24['chapters_count'])
print('Chapter Codes Identical?:', c22['chapter_codes'] == c24['chapter_codes'])

desc_diffs = []
for code, desc22 in c22['chapter_descriptions'].items():
    desc24 = c24['chapter_descriptions'].get(code)
    if desc22 != desc24:
        desc_diffs.append((code, desc22, desc24))
print(f'Chapter Descriptions identical?: {len(desc_diffs) == 0}')
if desc_diffs:
    print('Description diffs count:', len(desc_diffs))
    for d in desc_diffs:
        print('  Code', d[0], ':', repr(d[1]), 'vs', repr(d[2]))

print('\n=== NULL COUNTS COMPARISON ===')
print('Sheet 1 Matrix NULLs: 2022-23 =', s1_22['matrix_null_cells'], ', 2023-24 =', s1_24['matrix_null_cells'])
print('Sheet 2 NULLs: 2022-23 =', c22['null_values_count'], ', 2023-24 =', c24['null_values_count'])
print('Sheet 3 NULLs: 2022-23 =', p22['sheets']['Tab III_Outward_Revised_Road']['entity_details']['null_cells_in_data'], ', 2023-24 =', p24['sheets']['Tab III_Outward_Revised_Road']['entity_details']['null_cells_in_data'])
print('Sheet 4 NULLs: 2022-23 =', p22['sheets']['Tab IV_Inward_Revised_Road']['entity_details']['null_cells_in_data'], ', 2023-24 =', p24['sheets']['Tab IV_Inward_Revised_Road']['entity_details']['null_cells_in_data'])
print('Sheet 5 NULLs: 2022-23 =', p22['sheets']['Tab V_Internal_Revised_Road']['entity_details']['null_cells_in_data'], ', 2023-24 =', p24['sheets']['Tab V_Internal_Revised_Road']['entity_details']['null_cells_in_data'])

print('\n=== SUMMARY ROW 93 TOTALS ===')
print('Table II National Total: 2022-23 =', c22['reported_total_row_93'], ', 2023-24 =', c24['reported_total_row_93'])
print('Table IV Grand Total AK93: 2022-23 =', p22['sheets']['Tab IV_Inward_Revised_Road']['entity_details']['grand_total_cell_ak93'], ', 2023-24 =', p24['sheets']['Tab IV_Inward_Revised_Road']['entity_details']['grand_total_cell_ak93'])
print('Table V Grand Total AK93: 2022-23 =', p22['sheets']['Tab V_Internal_Revised_Road']['entity_details']['grand_total_cell_ak93'], ', 2023-24 =', p24['sheets']['Tab V_Internal_Revised_Road']['entity_details']['grand_total_cell_ak93'])
