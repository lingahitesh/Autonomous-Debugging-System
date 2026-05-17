import re
import os

def parse_fix(fix):
    fixes = []

    if "START_FIX" in fix:
        lines = fix.splitlines()
        for line in lines:
            if "START_FIX" in line or "END_FIX" in line:
                continue

            m = re.match(r'^([A-Za-z_][\w]*\.java):(\d+):\s*(.+)$', line.strip())
            if m:
                fixes.append((m.group(1), int(m.group(2)), m.group(3).strip()))
                continue

            m = re.match(r'^(\d+):\s*(.+)$', line.strip())
            if m:
                fixes.append((None, int(m.group(1)), m.group(2).strip()))

        return fixes

    else:
        line = fix.strip()

        m = re.match(r'^([A-Za-z_][\w]*\.java):(\d+):\s*(.+)$', line)
        if m:
            return [(m.group(1), int(m.group(2)), m.group(3).strip())]

        m = re.match(r'^(\d+):\s*(.+)$', line)
        if m:
            return [(None, int(m.group(1)), m.group(2).strip())]

        return []

def cleanup_backup(file_path):
    backup_path = file_path + ".bak"

    if os.path.exists(backup_path):
        os.remove(backup_path)

def apply_fix(file_path, line_no, new_code):
    backup_path = file_path + ".bak"

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(backup_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    lines = [line.rstrip("\n") for line in lines]

    while lines and not lines[-1].strip():
        lines.pop()

    new_code = new_code.strip()

    def get_indent(text):
        return text[:len(text) - len(text.lstrip())]

    if 0 < line_no <= len(lines):
        old_line = lines[line_no - 1]
        indentation = get_indent(old_line)

        # If new_code is a closing brace and the target line isn't one,
        # INSERT before the target line instead of replacing it
        if new_code.strip() in ("}", "};") and old_line.strip() not in ("}", "};"):
            lines.insert(line_no - 1, indentation + new_code)
        else:
            lines[line_no - 1] = indentation + new_code
    else:
        indentation = ""
        if lines:
            indentation = get_indent(lines[-1])
        lines.append(indentation + new_code)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")