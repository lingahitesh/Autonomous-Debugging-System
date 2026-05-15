import os

def parse_fix(fix):
    fixes=[]

    if "START_FIX" in fix:
        lines=fix.splitlines()
        for line in lines:
            if ":" in line and "START_FIX" not in line and "END_FIX" not in line:
                parts=line.split(":",2)

                try:
                    if len(parts)==3:
                        file_name=parts[0].strip()
                        line_no=int(parts[1].strip())
                        code=parts[2].strip()
                    else:
                        file_name=None
                        line_no=int(parts[0].strip())
                        code=parts[1].strip()

                    fixes.append((file_name,line_no,code))
                except:
                    continue
        return fixes

    else:
        parts=fix.split(":",2)
        try:
            if len(parts)==3:
                return [(parts[0].strip(),int(parts[1].strip()),parts[2].strip())]
            else:
                return [(None,int(parts[0].strip()),parts[1].strip())]
        except:
            return []

def apply_fix(file_path, line_no, new_code):
    backup_path = file_path + ".bak"

    with open(file_path, "r") as f:
        lines = f.readlines()
    with open(backup_path, "w") as f:
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
        lines[line_no - 1] = indentation + new_code

    else:
        indentation = ""
        if lines:
            indentation = get_indent(lines[-1])

        lines.append(indentation + new_code)

    with open(file_path, "w") as f:
        f.write("\n".join(lines) + "\n")

def undo_fix(file_path):
    backup_path = file_path + ".bak"

    if os.path.exists(backup_path):
        with open(backup_path, "r") as f:
            content = f.read()
        with open(file_path, "w") as f:
            f.write(content)

        print(f"↩️ Undo applied for {file_path}")