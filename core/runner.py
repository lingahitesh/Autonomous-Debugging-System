import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repair_loop import compile_phase, runtime_phase
from executor import run_java

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK_DIR = os.environ.get("WORK_DIR", os.path.join(BASE_DIR, "test"))

def main():
    class_name = "Main"
    compile_success = compile_phase(WORK_DIR)
    if not compile_success:
        print("\nCompilation could not be repaired.")
        return
    runtime_success = runtime_phase(WORK_DIR, class_name)
    if not runtime_success:
        print("\nRuntime could not be repaired.")
        return
    print("\n--- FINAL OUTPUT ---")
    result = run_java(class_name, WORK_DIR)
    print(result.stdout)

if __name__ == "__main__":
    main()