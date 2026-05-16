import re
import os

def parse_runtime_error(stderr):
    error_info = {}
    match_type = re.search(r'java\.lang\.(\w+)', stderr)

    if match_type:
        error_info["type"] = match_type.group(1)

    match_line = re.search(r'\((.*\.java):(\d+)\)', stderr)
    error_info["message"] = stderr.strip()

    if match_line:
        file_name = os.path.basename(match_line.group(1))
        error_info["file"] = file_name
        error_info["line"] = int(match_line.group(2))

    return error_info

def parse_compile_error(stderr):
    match = re.search(r'(.*\.java):(\d+): error: (.*)', stderr)

    if not match:
        return None

    return {
        "file": os.path.basename(
            os.path.normpath(match.group(1))
        ),
        "path": os.path.normpath(
            match.group(1)
        ),
        "line": int(
            match.group(2)
        ),
        "message": match.group(3)
    }