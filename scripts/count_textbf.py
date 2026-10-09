#!/usr/bin/env python3
"""Audit all \\textbf{} usages in thesis chapters."""
import re, os, json

CHAPTERS_DIR = r'd:\thesis\Chapters'

files = sorted(f for f in os.listdir(CHAPTERS_DIR) if f.endswith('.tex'))

results = {}
total_algo = 0
total_table = 0 
total_body = 0
body_details = []

for fname in files:
    fpath = os.path.join(CHAPTERS_DIR, fname)
    with open(fpath, encoding='utf-8') as f:
        lines = f.readlines()
    
    algo = 0
    table = 0
    body = 0
    
    for i, line in enumerate(lines):
        matches = list(re.finditer(r'\\textbf\{([^}]*)\}', line))
        if not matches:
            continue
        
        is_algo = any(kw in line for kw in [
            '\\STATE', '\\RETURN', '\\IF', '\\ELSE', '\\FOR', 
            '\\WHILE', '\\LOOP', '\\hspace', '\\REQUIRE', '\\ENSURE'
        ])
        is_table_line = ('multicolumn' in line or 
                         '\\hline' in line or 
                         '\\toprule' in line or
                         '\\midrule' in line or
                         '\\bottomrule' in line)
        is_table_data = ('&' in line and '\\\\' in line)
        
        for m in matches:
            content = m.group(1).strip()
            lineno = i + 1
            if is_algo:
                algo += 1
            elif is_table_line or is_table_data:
                table += 1
            else:
                body += 1
                body_details.append({
                    'file': fname,
                    'line': lineno,
                    'content': content,
                    'context': line.strip()[:120]
                })
    
    if algo + table + body > 0:
        results[fname] = {'algo': algo, 'table': table, 'body': body, 'total': algo+table+body}
        print(f'{fname:35s}  algo={algo:3d}  table={table:3d}  body={body:3d}  total={algo+table+body:3d}')
    total_algo += algo
    total_table += table
    total_body += body

print('-'*85)
print(f'{"TOTAL":35s}  algo={total_algo:3d}  table={total_table:3d}  body={total_body:3d}  total={total_algo+total_table+total_body:3d}')
print()
print(f'=== Body text \\textbf occurrences (need correction): {total_body} ===')
print()

for item in body_details:
    print(f"  {item['file']}:{item['line']:4d}  \\textbf{{{item['content'][:50]}}}")
