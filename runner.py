import subprocess
import os
from parser import parse_runtime_error
from parser import parse_compile_error
from context import extract_context
from ai import generate_fix

def compile_java(file_path):
    result=subprocess.run(
        ["javac", file_path],
        capture_output=True,
        text=True
    )
    return result

def run_java(class_name, cwd):
    result=subprocess.run(
        ["java", class_name],
        capture_output=True,
        text=True,
        cwd=cwd
    )
    return result

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

def main():
    file_path="test/Main.java"
    directory="test"
    class_name="Main"

    MAX_ATTEMPTS = 5

    attempt = 0

    while attempt < MAX_ATTEMPTS:
        print(f"\n--- Attempt {attempt + 1} ---")

        compile_result = compile_java(file_path)

        if compile_result.returncode == 0:
            print("✅ Compilation Successful!")
            break

        print("❌ Compilation Failed")

        parsed = parse_compile_error(compile_result.stderr)

        if not parsed:
            print("Could not parse error")
            break

        context = extract_context(file_path, parsed["line"])

        print("\n--- CODE CONTEXT ---")
        for line in context:
            print(line)

        fix = generate_fix(parsed, context)

        print("\n--- AI FIX ---")
        print(fix)

        line_no, new_code = parse_fix(fix)

        if not line_no:
            print("Invalid fix format")
            break

        apply_fix(file_path, line_no, new_code)

        attempt += 1
        last_fix = None

        if fix == last_fix:
            print("⚠️ Same fix repeating, stopping")
            break

        last_fix = fix

if __name__=="__main__":
    main()