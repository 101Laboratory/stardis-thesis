#!/usr/bin/env python3
"""Remove mid-paragraph \\textbf{} from thesis chapters, keeping paragraph-initial ones.
Usage:
    python scripts/fix_textbf.py          # dry-run
    python scripts/fix_textbf.py --apply  # actually write files
"""
import re, os, sys

CHAPTERS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Chapters')
FILES = [
    '1_Introduction.tex',
    '2_Research.tex',
    '3_ParallelizedSolver.tex',
    '4_RTBackend.tex',
    '5_GUI.tex',
    '6_Conclusion.tex',
]

def find_matching_brace(text, start):
    """Find matching '}' for '{' at position start."""
    depth = 0
    i = start
    while i < len(text):
        # Skip escaped braces
        if text[i] == '\\' and i + 1 < len(text) and text[i + 1] in '{}':
            i += 2
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1

def is_in_special_env(line, in_algo_env):
    """Check if line is inside algorithm or table environment (skip these)."""
    if in_algo_env:
        return True
    algo_kw = ['\\STATE', '\\RETURN', '\\IF{', '\\IF ', '\\ELSE',
               '\\FOR{', '\\FOR ', '\\WHILE', '\\LOOP', '\\REQUIRE',
               '\\ENSURE', '\\hspace', '\\ENDFOR', '\\ENDIF', '\\ENDWHILE',
               '\\COMMENT', '\\algorithmic']
    for kw in algo_kw:
        if kw in line:
            return True
    # Table data lines
    if 'multicolumn' in line:
        return True
    if '&' in line and '\\\\' in line:
        return True
    return False

def is_paragraph_initial(line, match_pos):
    """Check if \\textbf at match_pos is at the start of a paragraph/item."""
    before = line[:match_pos]
    stripped = before.strip()

    # Nothing before
    if stripped == '':
        return True
    # \item before (with optional whitespace)
    if re.match(r'^\\item\s*$', stripped):
        return True
    # Numbering: （1）, （一）, (1), etc.
    if re.match(r'^[（\(]\s*[0-9一二三四五六七八九十]+\s*[）\)]\s*$', stripped):
        return True
    # \item + numbering
    if re.match(r'^\\item\s+[（\(][0-9一二三四五六七八九十]+[）\)]$', stripped):
        return True
    return False

def process_file(filepath, dry_run=True):
    """Process a single .tex file. Returns list of (lineno, removed_content)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    changes = []
    keeps = []
    new_lines = []
    in_algo_env = False

    for line_idx, line in enumerate(lines):
        lineno = line_idx + 1

        # Track algorithm environment
        if '\\begin{algorithmic}' in line or '\\begin{algorithm}' in line:
            in_algo_env = True
        if '\\end{algorithmic}' in line or '\\end{algorithm}' in line:
            in_algo_env = False
            new_lines.append(line)
            continue

        if is_in_special_env(line, in_algo_env) or '\\textbf{' not in line:
            new_lines.append(line)
            continue

        # Process line: find each \textbf{...} and decide keep/remove
        new_line = ''
        pos = 0

        while pos < len(line):
            idx = line.find('\\textbf{', pos)
            if idx == -1:
                new_line += line[pos:]
                break

            brace_start = idx + 7  # position of '{'
            brace_end = find_matching_brace(line, brace_start)
            if brace_end == -1:
                new_line += line[pos:]
                break

            content_inside = line[brace_start + 1:brace_end]

            if is_paragraph_initial(new_line + line[pos:idx], idx - (len(line) - len(line[pos:]))):
                # Re-check with accumulated new_line for proper context
                pass

            # For paragraph-initial check, use the ORIGINAL line up to idx
            if is_paragraph_initial(line, idx):
                new_line += line[pos:brace_end + 1]
                keeps.append((lineno, content_inside[:60]))
            else:
                new_line += line[pos:idx]
                new_line += content_inside
                changes.append((lineno, content_inside[:60]))

            pos = brace_end + 1

        new_lines.append(new_line)

    new_content = '\n'.join(new_lines)

    if not dry_run and new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

    return changes, keeps


def main():
    dry_run = '--apply' not in sys.argv
    mode = 'DRY RUN' if dry_run else 'APPLYING'
    print(f'=== {mode} ===\n')

    total_removed = 0
    total_kept = 0

    for fname in FILES:
        fpath = os.path.join(CHAPTERS_DIR, fname)
        if not os.path.exists(fpath):
            print(f'  [SKIP] {fname} not found')
            continue

        changes, keeps = process_file(fpath, dry_run=dry_run)
        if changes or keeps:
            print(f'{fname}:')
            if keeps:
                print(f'  KEEP ({len(keeps)}):')
                for lineno, content in keeps:
                    print(f'    L{lineno}: \\textbf{{{content}}}')
            if changes:
                print(f'  REMOVE ({len(changes)}):')
                for lineno, content in changes:
                    print(f'    L{lineno}: \\textbf{{{content}}} -> {content}')
            print()
        total_removed += len(changes)
        total_kept += len(keeps)

    print(f'{"=" * 60}')
    print(f'Total: {total_removed} removed, {total_kept} kept (body text)')
    print(f'(Algorithm/table \\textbf are untouched)')
    if dry_run:
        print(f'\nRe-run with --apply to write changes.')


if __name__ == '__main__':
    main()
