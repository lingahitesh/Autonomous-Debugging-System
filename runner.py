import subprocess
import os
from parser import parse_runtime_error, parse_compile_error
from context import extract_context, find_related_files_recursive, extract_suspicious_region
from ai import generate_fix, verify_fix
from fixer import parse_fix, apply_fix
from scorer import score_file
from strategy import choose_strategy
from memory import remember_fix, recall_fix

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

def compile_single_java(java_file, directory):
    return subprocess.run(
        ["javac", java_file],
        capture_output=True,
        text=True,
        cwd=directory
    )

def compile_java(directory):
    return subprocess.run(
        ["javac", "*.java"],
        capture_output=True,
        text=True,
        cwd=directory,
        shell=True
    )

def run_java(class_name, cwd):
    try:
        process = subprocess.Popen(
            ["java", class_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd
        )
        try:
            stdout, stderr = process.communicate(timeout=10)
            return subprocess.CompletedProcess(
                args=["java", class_name],
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr
            )
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return subprocess.CompletedProcess(
                args=["java", class_name],
                returncode=-1,
                stdout="",
                stderr="TIMEOUT"
            )
    except Exception:
        return None

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

def main():
    file_path = "test/Main.java"
    directory = "test"
    class_name = "Main"
    max_attempts = 5

    # =========================
    # COMPILE LOOP
    # =========================
    attempt = 0
    seen_fixes = set()

    while attempt < max_attempts:
        print(f"\n--- Compile Attempt {attempt + 1} ---")
        compile_result = compile_java(directory)

        if compile_result.returncode == 0:
            print("✅ Compilation Successful!")
            break

        print("❌ Compilation Failed")
        parsed = parse_compile_error(compile_result.stderr)

        if not parsed:
            print("Could not parse compile error")
            break

        base_dir = os.path.dirname(file_path)
        full_path = os.path.join(base_dir, parsed["file"])
        context = extract_context(full_path, parsed["line"])

        print("\n--- CODE CONTEXT (COMPILE ERROR) ---")
        for line in context:
            print(line)

        strategy = choose_strategy(parsed)
        print("\n[DEBUG] Strategy:", strategy)
        local_key, global_key = build_error_keys(parsed, strategy)
        fix = recall_fix(local_key)

        if not fix and ("end of file" in parsed.get("message", "").lower()):
            fix = recall_fix(global_key)

        if fix:
            print("\n[MEMORY] Reusing known fix")
        else:
            fix = generate_fix(parsed, context, strategy)
            print("\n--- AI FIX ---")
            print(fix)

        fixes = parse_fix(fix)

        if not fixes:
            print("Invalid fix format")
            break

        fix_signature = f"{local_key}:{fix.strip()}"

        if fix_signature in seen_fixes:
            print("⚠️ Fix already tried, stopping")
            break

        seen_fixes.add(fix_signature)
        verification = verify_fix(parsed, context, fix)
        print("\n--- VERIFICATION ---")
        print(verification)

        if verification != "VALID":
            print("❌ Fix rejected by verifier")
            attempt += 1
            continue
        else:
            remember_fix(local_key, fix)
            remember_fix(global_key, fix)

        changed_files = set()

        for file_name, line_no, new_code in fixes:
            target_file = file_name if file_name else parsed.get("file")
            target_path = os.path.join(base_dir, target_file)
            changed_files.add(target_file)

            if not os.path.exists(target_path):
                print(f"⚠️ Skipping invalid target file: {target_file}")
                continue

            apply_fix(target_path, line_no, new_code)

        compile_failed = False

        for changed_file in changed_files:
            compile_result = compile_single_java(
                changed_file,
                directory
            )

            if compile_result.returncode != 0:
                compile_failed = True
                break

        if compile_failed:
            print("⚠️ Fix broke compilation")
            break

        attempt += 1

    # =========================
    # RUN LOOP
    # =========================
    attempt = 0
    seen_fixes = set()

    while attempt < max_attempts:
        print(f"\n--- Run Attempt {attempt + 1} ---")
        run_result = run_java(class_name, directory)

        if run_result.returncode == -1:
            print("❌ Program Timeout (possible infinite loop)")
            parsed = {
                "message": "Program stuck in infinite loop. Check loop condition and update expression.",
                "line": None,
                "file": os.path.basename(file_path)
            }
        else:
            if run_result.returncode == 0 and is_output_valid(run_result.stdout):
                print("✅ Running Successful")
                break

            print("❌ Output invalid or runtime issue")

            if run_result.stderr:
                parsed = parse_runtime_error(run_result.stderr)
            else:
                parsed = {
                    "message": "Program produced incorrect output",
                    "file": os.path.basename(file_path),
                    "line": None
                }

            if not parsed:
                print("Could not parse runtime error")
                break

        base_dir = os.path.dirname(file_path)
        entry_file = parsed.get("file", os.path.basename(file_path))
        files = find_related_files_recursive(entry_file, base_dir)
        files = sorted(files, key=lambda f: score_file(f, entry_file), reverse=True)
        print("\n[DEBUG] File priority order:", files)

        context = []

        for file in files:
            path = os.path.join(base_dir, file)
            context += [f"\n--- {file} ---"]
            region = extract_suspicious_region(path)

            if region:
                context += region
            else:
                context += extract_context(path, None)

        if len(context) > 300:
            context = context[-300:]

        print("\n--- CODE CONTEXT (RUNTIME ERROR) ---")
        for line in context:
            print(line)

        strategy = choose_strategy(parsed)
        print("\n[DEBUG] Strategy:", strategy)
        local_key, global_key = build_error_keys(parsed, strategy)
        fix = recall_fix(local_key)

        if not fix and ("end of file" in parsed.get("message", "").lower()):
            fix = recall_fix(global_key)

        if fix:
            print("\n[MEMORY] Reusing known fix")
        else:
            fix = generate_fix(parsed, context, strategy)
            print("\n--- AI FIX ---")
            print(fix)

        fixes = parse_fix(fix)

        if not fixes:
            print("Invalid fix format")
            break

        fix_signature = f"{local_key}:{fix.strip()}"

        if fix_signature in seen_fixes:
            print("⚠️ Fix already tried, stopping")
            break

        seen_fixes.add(fix_signature)
        verification = verify_fix(parsed, context, fix)

        print("\n--- VERIFICATION ---")
        if verification == "VALID":
            print(verification)
            remember_fix(local_key, fix)
            remember_fix(global_key, fix)
        else:
            print("❌ Fix rejected")
            attempt += 1
            continue

        changed_files = set()

        for file_name, line_no, new_code in fixes:
            target_file = file_name if file_name else parsed.get("file")
            target_path = os.path.join(base_dir, target_file)
            changed_files.add(target_file)

            if not os.path.exists(target_path):
                print(f"⚠️ Skipping invalid target file: {target_file}")
                continue

            apply_fix(target_path, line_no, new_code)

        compile_failed = False

        for changed_file in changed_files:
            compile_result = compile_single_java(
                changed_file,
                directory
            )

            if compile_result.returncode != 0:
                compile_failed = True
                break

        if compile_failed:
            print("⚠️ Fix broke compilation")
            break

        attempt += 1

    print("\n--- OUTPUT ---")
    final_run = run_java(class_name, directory)

    if final_run.returncode == 0:
        print(final_run.stdout)
        print("\n--- ERRORS ---")
        print(final_run.stderr)
    else:
        print("Program still not terminating")

if __name__ == "__main__":
    main()