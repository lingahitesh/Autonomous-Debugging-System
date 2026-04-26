import subprocess
import os
from parser import parse_runtime_error, parse_compile_error
from context import extract_context
from ai import generate_fix, verify_fix
from fixer import parse_fix, apply_fix

def compile_java(directory):
    return subprocess.run(
        ["javac", "*.java"],
        capture_output=True,
        text=True,
        cwd=directory,
        shell=True   # 🔥 needed for wildcard
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
            stdout, stderr = process.communicate(timeout=3)
            return subprocess.CompletedProcess(
                args=["java", class_name],
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr
            )
        except subprocess.TimeoutExpired:
            process.kill()  # 🔥 IMPORTANT
            process.wait()  # 🔥 CLEANUP
            return "TIMEOUT"
    except Exception as e:
        return None

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

        fix = generate_fix(parsed, context)
        print("\n--- AI FIX ---")
        print(fix)
        line_no, new_code = parse_fix(fix)

        if line_no is None or new_code is None:
            print("Invalid fix format")
            break

        if fix in seen_fixes:
            print("⚠️ Fix already tried, stopping")
            break

        seen_fixes.add(fix)
        verification = verify_fix(parsed, context, fix)
        print("\n--- VERIFICATION ---")
        print(verification)

        if verification != "VALID":
            print("⚠️ Verifier uncertain, continuing anyway...")

        apply_fix(full_path, line_no, new_code)
        attempt += 1

    # =========================
    # RUN LOOP
    # =========================
    attempt = 0
    seen_fixes = set()

    while attempt < max_attempts:
        print(f"\n--- Run Attempt {attempt + 1} ---")
        run_result = run_java(class_name, directory)

        if run_result == "TIMEOUT":
            print("❌ Program Timeout (possible infinite loop)")
            parsed = {
                "message": "Program stuck in infinite loop. Check loop condition and update expression.",
                "line": None,
                "file": file_path  # 🔥 FIX 2: ensure file exists
            }
        else:
            if run_result.returncode == 0:
                print("✅ Running Successful")
                break

            print("❌ Running Failed")
            parsed = parse_runtime_error(run_result.stderr)

            if not parsed:
                print("Could not parse runtime error")
                break

        base_dir = os.path.dirname(file_path)
        full_path = os.path.join(base_dir, parsed.get("file", os.path.basename(file_path)))
        context = extract_context(full_path, parsed.get("line"))

        print("\n--- CODE CONTEXT (RUNTIME ERROR) ---")
        for line in context:
            print(line)

        fix = generate_fix(parsed, context)
        print("\n--- AI FIX ---")
        print(fix)
        line_no, new_code = parse_fix(fix)

        if line_no is None or new_code is None:
            print("Invalid fix format")
            break

        if fix in seen_fixes:
            print("⚠️ Fix already tried, stopping")
            break

        seen_fixes.add(fix)
        verification = verify_fix(parsed, context, fix)

        print("\n--- VERIFICATION ---")
        if verification== "VALID":
            print(verification)

        if verification != "VALID":
            print("⚠️ Verifier uncertain, continuing anyway...")

        apply_fix(full_path, line_no, new_code)
        compile_result = compile_java(full_path)

        if compile_result.returncode != 0:
            print("⚠️ Fix broke compilation")
            break
        attempt += 1

    print("\n--- OUTPUT ---")
    final_run = run_java(class_name, directory)
    if final_run != "TIMEOUT":
        print(final_run.stdout)
        print("\n--- ERRORS ---")
        print(final_run.stderr)
    else:
        print("Program still not terminating")

if __name__ == "__main__":
    main()