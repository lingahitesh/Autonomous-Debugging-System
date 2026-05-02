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
    with open(file_path, "r") as f:
        lines = f.readlines()

    new_code = new_code.strip()

    if 0 < line_no <= len(lines):
        old_line = lines[line_no - 1]

        indentation = old_line[:len(old_line) - len(old_line.lstrip())]

        lines[line_no - 1] = indentation + new_code + "\n"

    else:
        indentation = ""

        if lines:
            last_line = lines[-1]

            indentation = last_line[:len(last_line) - len(last_line.lstrip())]

            if new_code == "}" and last_line.strip() == "}":
                indentation = indentation[:-4] if len(indentation) >= 4 else ""

        lines.append(indentation + new_code + "\n")

    with open(file_path, "w") as f:
        f.writelines(lines)