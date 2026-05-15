def sanitize_fixes(fixes, parsed_file):
    cleaned = []
    seen = set()

    for file_name, line_no, new_code in fixes:
        target = file_name if file_name else parsed_file

        # skip invalid stuff
        if not target:
            continue
        if not isinstance(line_no, int):
            continue
        if not new_code or not new_code.strip():
            continue

        code = new_code.strip()
        # skip comments
        if code.startswith("//"):
            continue
        # remove duplicates
        key = (target, line_no)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append((target, line_no, code))

    # limit number of fixes
    return cleaned[:3]

def is_output_valid(output):
    if not output.strip():
        return False

    lines = output.strip().split("\n")

    for line in lines:
        if "Result:" not in line:
            return False
        try:
            value = int(line.split(":")[1].strip())
            if value < 0 or value > 1000:
                return False
        except:
            return False

    return True