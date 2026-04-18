import re
import os

def parse_runtime_error(stderr):
    error_info={}

    # Extract exception type
    match_type=re.search(r'java\.lang\.(\w+)',stderr)
    if match_type:
        error_info["type"]=match_type.group(1)

    # Extract file and line number
    match_line=re.search(r'\((.*\.java):(\d+)\)',stderr)
    if match_line:
        full_path=os.path.normpath(match_line.group(1))
        error_info["file"]=match_line.group(1)
        error_info["path"]=full_path
        error_info["line"]=int(match_line.group(2))

    return error_info

def parse_compile_error(stderr):
    error_info={}

    match=re.search(r'(.*\.java):(\d+): error: (.*)',stderr)
    if match:
        full_path=os.path.normpath(match.group(1))
        print(stderr)
        error_info["file"]=os.path.basename(full_path)
        error_info["path"]=full_path
        error_info["line"]=int(match.group(2))
        error_info["message"]=match.group(3)

    return error_info