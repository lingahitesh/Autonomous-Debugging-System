import subprocess
import os
from parser import parse_runtime_error
from parser import parse_compile_error

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
        return
    else:
        print("Compilation Successful")

    print("\nRunning...")
    run_result=run_java(class_name, directory)

    parsed = parse_runtime_error(run_result.stderr)
    print("\n--- PARSED RUNTIME ERROR ---")
    print(parsed)

    print("\n--- OUTPUT ---")
    print(run_result.stdout)

    print("\n--- ERRORS ---")
    print(run_result.stderr)

if __name__=="__main__":
    main()