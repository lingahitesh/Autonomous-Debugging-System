import subprocess
import os
from parser import parse_runtime_error, parse_compile_error
from context import extract_context
from ai import generate_fix, verify_fix
from fixer import parse_fix, apply_fix

def compile_java(file_path):
    return subprocess.run(
        ["javac", file_path],
        capture_output=True,
        text=True
    )


def run_java(class_name, cwd):
    return subprocess.run(
        ["java", class_name],
        capture_output=True,
        text=True,
        cwd=cwd
    )


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

        compile_result = compile_java(file_path)

        if compile_result.returncode == 0:
            print("✅ Compilation Successful!")
            break

        print("❌ Compilation Failed")

        parsed = parse_compile_error(compile_result.stderr)
        if not parsed:
            print("Could not parse compile error")
            break

        context = extract_context(file_path, parsed["line"])

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

        # 🔥 Prevent repeated fixes
        if fix in seen_fixes:
            print("⚠️ Fix already tried, stopping")
            break
        seen_fixes.add(fix)

        # 🔥 Verify fix
        verification = verify_fix(parsed, context, fix)

        print("\n--- VERIFICATION ---")
        print(verification)

        if verification != "VALID":
            print("⚠️ Verifier uncertain, continuing anyway...")

        # 🔥 Apply fix
        apply_fix(file_path, line_no, new_code)

        attempt += 1

    # =========================
    # RUN LOOP
    # =========================
    attempt = 0
    seen_fixes = set()

    while attempt < max_attempts:
        print(f"\n--- Run Attempt {attempt + 1} ---")

        run_result = run_java(class_name, directory)

        if run_result.returncode == 0:
            print("✅ Running Successful")
            break

        print("❌ Running Failed")

        parsed = parse_runtime_error(run_result.stderr)
        if not parsed:
            print("Could not parse runtime error")
            break

        base_dir = os.path.dirname(file_path) or "."
        full_path = os.path.join(base_dir, parsed["file"])

        context = extract_context(full_path, parsed["line"])

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

        # 🔥 Prevent repeated fixes
        if fix in seen_fixes:
            print("⚠️ Fix already tried, stopping")
            break
        seen_fixes.add(fix)

        # 🔥 Verify fix
        verification = verify_fix(parsed, context, fix)

        print("\n--- VERIFICATION ---")
        print(verification)

        if verification != "VALID":
            print("⚠️ Verifier uncertain, continuing anyway...")

        # 🔥 Apply fix to correct file
        apply_fix(full_path, line_no, new_code)

        # 🔥 Recompile after runtime fix
        compile_result = compile_java(file_path)

        if compile_result.returncode != 0:
            print("⚠️ Fix broke compilation")
            break

        attempt += 1

    print("\n--- OUTPUT ---")
    print(run_java(class_name, directory).stdout)

    print("\n--- ERRORS ---")
    print(run_java(class_name, directory).stderr)


if __name__ == "__main__":
    main()