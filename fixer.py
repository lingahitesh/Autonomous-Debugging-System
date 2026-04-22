def parse_fix(fix):
    try:
        line_no, code = fix.split(":", 1)
        return int(line_no.strip()), code.strip()
    except:
        return None, None

def apply_fix(file_path, line_no, new_code):
    with open(file_path, "r") as f:
        lines = f.readlines()

    old_line = lines[line_no - 1]

    # extract indentation (spaces/tabs at start)
    indentation = old_line[:len(old_line) - len(old_line.lstrip())]

    # apply fix with same indentation
    lines[line_no - 1] = indentation + new_code + "\n"

    with open(file_path, "w") as f:
        f.writelines(lines)

