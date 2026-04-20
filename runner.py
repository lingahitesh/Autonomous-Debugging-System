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

def main():
    file_path="test/Main.java"
    directory="test"
    class_name="Main"

    print("Compiling...")
    compile_result=compile_java(file_path)

    if compile_result.returncode!=0:
        print("Compilation Failed")
        parsed = parse_compile_error(compile_result.stderr)
        print("\n--- PARSED COMPILE ERROR ---")
        print(parsed)
        if parsed:
            context = extract_context(parsed["path"], parsed["line"])
            print("\n--- CODE CONTEXT (COMPILE ERROR) ---")
            for line in context:
                print(line)

            fix = generate_fix(parsed, context)

            print("\n--- AI FIX ---")
            print(fix)
        return
    else:
        print("Compilation Successful")

    print("\nRunning...")
    run_result=run_java(class_name, directory)

    if run_result.returncode!=0:
        print("Running Failed")
        parsed = parse_runtime_error(run_result.stderr)
        print("\n--- PARSED RUNTIME ERROR ---")
        print(parsed)
        if parsed:
            base_dir = os.path.dirname(file_path) or "."
            full_path = os.path.join(base_dir, parsed["file"])

            context = extract_context(full_path, parsed["line"])
            print("\n--- CODE CONTEXT (RUNTIME ERROR) ---")
            for line in context:
                print(line)

            fix = generate_fix(parsed, context)

            print("\n--- AI FIX ---")
            print(fix)
    else:
        print("Running Successful")

    print("\n--- OUTPUT ---")
    print(run_result.stdout)

    print("\n--- ERRORS ---")
    print(run_result.stderr)

if __name__=="__main__":
    main()