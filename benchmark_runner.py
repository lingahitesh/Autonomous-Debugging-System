import os
import time
import shutil
import subprocess
import difflib
import sys
import json

BASE_DIR = os.getcwd() #C:\Users\KIIT\PycharmProjects\DebuggingAgent
BENCHMARK_DIR = os.path.join(BASE_DIR, "benchmark")
TEST_DIR = os.path.join(BASE_DIR, "test")

TOTAL = 0
SUCCESS = 0
SCORES = []
ATTEMPTS = []
TIMES = []

# -----------------------------
# RUN AGENT
# -----------------------------
def run_agent(work_dir):
    start = time.time()

    process = subprocess.Popen(
        [sys.executable, os.path.join('core', 'runner.py')],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
        cwd=BASE_DIR,
        env={**os.environ, "WORK_DIR": work_dir} # Send env variables to child process
    )

    stdout, stderr = process.communicate() # Extraction of output and errors

    if stdout is None:
        stdout = ""
    if stderr:
        print("STDERR:", stderr)

    end = time.time()
    return stdout, stderr, end - start

# -----------------------------
# PARSE OUTPUT
# -----------------------------
def extract_result(output):
    if not output:
        return None

    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("Result:"):
            return line.split(":",1)[1].strip() # Result after line no. with only first :

    return None

# -----------------------------
# DIFF VIEW
# -----------------------------
def show_diff(original_lines, modified_lines):
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile="before",
        tofile="after",
        lineterm="" # no extra lines
    )
    print("\n".join(diff))

# -----------------------------
# MULTI-SIGNAL EVALUATION
# -----------------------------
def evaluate(work_dir, output, stderr):
    score = 0

    if "Compilation Successful"  in output:
        score += 0.3
    if "Program Timeout" not in output and stderr == "":
        score += 0.3

    results = []
    # Run code thrice and extract set of results that successfully ran
    for _ in range(3):
        stdout_i, stderr_i, _ = run_agent(work_dir)

        if stderr_i or "Program Timeout" in stdout_i:
            continue

        r = extract_result(stdout_i)
        if r is not None:
            results.append(r)
    # Result produced
    if len(results) > 0:
        score += 0.2
    # Consistency score
    if len(results) >= 2:
        most_common = max(set(results), key=results.count)
        count = results.count(most_common)

        if count >= 2:
            score += 0.2

    return score

# -----------------------------
# ATTEMPT COUNT
# -----------------------------
def count_attempts(output):
    return max(output.count("Attempt"), 1)

# -----------------------------
# RESET TEST DIR
# -----------------------------
def reset_test_dir(source_dir):
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR) # removes test directory

    shutil.copytree(source_dir, TEST_DIR) # copies entire test case into test directory

    for file in os.listdir(TEST_DIR):
        if file.endswith(".class"):
            os.remove(os.path.join(TEST_DIR, file)) # remove .class files

# -----------------------------
# BENCHMARK LOOP
# -----------------------------
def run_benchmark():
    global TOTAL, SUCCESS
    cases = sorted(os.listdir(BENCHMARK_DIR))

    for case in cases:
        case_path = os.path.join(BENCHMARK_DIR, case)

        if not os.path.isdir(case_path):
            continue

        print(f"\n=== Running {case} ===")
        reset_test_dir(case_path)
        TOTAL += 1
        stdout, stderr, duration = run_agent(TEST_DIR)
        print(stdout)
        score = evaluate(TEST_DIR, stdout, stderr)
        attempts = count_attempts(stdout)
        SCORES.append(score)
        ATTEMPTS.append(attempts)
        TIMES.append(duration)

        if score >= 0.7:
            SUCCESS += 1
            print(f"✅ PASS (score={score:.2f})")
        else:
            print(f"❌ FAIL (score={score:.2f})")
    print_summary()

# -----------------------------
# SUMMARY
# -----------------------------
def print_summary():
    avg_score = sum(SCORES) / len(SCORES)
    avg_attempts = sum(ATTEMPTS) / len(ATTEMPTS)
    avg_time = sum(TIMES) / len(TIMES)
    success_rate = (SUCCESS / TOTAL) * 100

    print("\n===== BENCHMARK RESULTS =====")
    print(f"Total Cases: {TOTAL}")
    print(f"Solved: {SUCCESS}")
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"Avg Score: {avg_score:.2f}")
    print(f"Avg Attempts: {avg_attempts:.2f}")
    print(f"Avg Time: {avg_time:.2f} sec")

    report = {
        "total": TOTAL,
        "success": SUCCESS,
        "success_rate": success_rate,
        "scores": SCORES,
        "attempts": ATTEMPTS,
        "times": TIMES
    }
    # Result file
    with open(os.path.join(BASE_DIR, "benchmark_results.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

# -----------------------------
# ENTRY
# -----------------------------
if __name__ == "__main__":
    run_benchmark()