import os
from parser import parse_compile_error, parse_runtime_error
from context import extract_context, find_related_files_recursive, extract_suspicious_region
from ai import generate_fix, verify_fix
from fixer import parse_fix, apply_fix
from scorer import score_file
from strategy import choose_strategy
from memory import remember_fix, recall_fix
from executor import compile_java, run_java
from session import create_session_backup, restore_session_backup
from validator import sanitize_fixes, is_output_valid

MAX_ATTEMPTS = 5

def build_error_keys(parsed, strategy):
    message = parsed.get("message", "").lower()
    file_name = parsed.get("file", "unknown")
    line = parsed.get("line", "x")

    if "timeout" in message:
        error_type = "timeout"
    elif "end of file" in message:
        error_type = "eof"
    else:
        error_type = "generic"

    local_key = f"{file_name}_{line}_{error_type}_{strategy}"
    global_key = f"{error_type}_{strategy}"
    return local_key, global_key

def attempt_repair(parsed, context, base_dir, work_dir, seen_fixes):
    strategy = choose_strategy(parsed)
    local_key, global_key = build_error_keys(parsed, strategy)
    fix = recall_fix(local_key)

    if fix:
        candidate_fixes = [fix]
    else:
        candidate_fixes = []

    for _ in range(3):
        if not candidate_fixes:
            current_fix = generate_fix(parsed, context, strategy)
        else:
            current_fix = candidate_fixes.pop(0)

        normalized_fix = " ".join(current_fix.lower().split())
        signature = f"{local_key}:{normalized_fix}"

        if signature in seen_fixes:
            continue

        fixes = parse_fix(current_fix)

        if not fixes:
            continue

        safe_fixes = sanitize_fixes(fixes, parsed.get("file"))

        if not safe_fixes:
            continue

        verification = verify_fix(parsed, context, current_fix)
        seen_fixes.add(signature)

        if verification != "VALID":
            continue

        files_to_backup = []

        for file_name, _, _ in safe_fixes:
            files_to_backup.append(file_name)

        backup = create_session_backup(files_to_backup, base_dir)

        try:
            for file_name, line_no, code in safe_fixes:
                file_path = os.path.join(base_dir, file_name)

                if not os.path.exists(file_path):
                    raise Exception("Invalid file target")

                apply_fix(file_path, line_no, code)
                print(f"Applied fix: {file_name}:{line_no}")

            compile_result = compile_java(work_dir)

            if compile_result.returncode != 0:
                raise Exception("Compilation failed")

            remember_fix(local_key, current_fix)
            remember_fix(global_key, current_fix)

            return True

        except Exception:
            print("Rolling back bad fix...")
            restore_session_backup(backup, base_dir)

    print("No valid repair found")

    return False

def compile_phase(work_dir):
    file_path = os.path.join(work_dir,"Main.java")
    base_dir = os.path.dirname(file_path)
    attempt = 0
    seen_fixes = set()
    while attempt < MAX_ATTEMPTS:
        print(f"\n--- Compile Attempt {attempt + 1} ---")
        compile_result = compile_java(work_dir)
        if compile_result.returncode == 0:
            print("Compilation Successful")
            return True
        parsed = parse_compile_error(compile_result.stderr)
        if not parsed:
            return False
        context = extract_context(
            os.path.join(base_dir,parsed["file"]),
            parsed["line"]
        )
        fixed = attempt_repair(parsed,context,base_dir,work_dir,seen_fixes)
        if not fixed:
            attempt += 1
            continue
        attempt += 1
    return False


def runtime_phase(work_dir, class_name):
    file_path = os.path.join(work_dir,"Main.java")
    base_dir = os.path.dirname(file_path)
    attempt = 0
    seen_fixes = set()
    while attempt < MAX_ATTEMPTS:
        print(f"\n--- Run Attempt {attempt + 1} ---")
        result = run_java(class_name,work_dir)
        if result.returncode == 0 and is_output_valid(result.stdout):
            print("Running Successful")
            return True
        if result.returncode == -1:
            parsed = {
                "message":"timeout",
                "file":"Main.java",
                "line":None
            }
        else:
            parsed = parse_runtime_error(result.stderr)
            if not parsed:
                parsed = {
                    "message":"output mismatch",
                    "file":"Main.java",
                    "line":None
                }
        entry_file = parsed.get("file")
        if not entry_file:
            entry_file = "Main.java"
        files = find_related_files_recursive(entry_file,base_dir)
        files = sorted(
            files,
            key=lambda f: score_file(f,entry_file),
            reverse=True
        )
        context = []
        for file in files:
            path = os.path.join(base_dir,file)
            context.append(f"\n--- {file} ---")
            region = extract_suspicious_region(path)
            if region:
                context += region
            else:
                context += extract_context(path,None)
        fixed = attempt_repair(parsed,context,base_dir,work_dir,seen_fixes)
        if not fixed:
            attempt += 1
            continue
        attempt += 1
    return False