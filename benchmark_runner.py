import os
import time
import shutil
import subprocess

BASE_DIR = os.getcwd()
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
def run_agent():
    start = time.time()

    process = subprocess.Popen(
        [os.sys.executable, "runner.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
        cwd=BASE_DIR
    )

    stdout, stderr = process.communicate()

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
            try:
                return int(line.split(":")[1].strip())
            except:
                return None

    return None


# -----------------------------
# MULTI-SIGNAL EVALUATION
# -----------------------------
def evaluate(output, stderr):
    score = 0

    # 1. Compilation success
    if "Compilation Failed" not in output:
        score += 0.3

    # 2. Runtime success
    if "Program Timeout" not in output and stderr == "":
        score += 0.3

    # 3. Run multiple times to remove dependency on first run
    results = []
    runs = 3

    for _ in range(runs):
        try:
            stdout_i, stderr_i, _ = run_agent()

            if stderr_i or "Program Timeout" in stdout_i:
                continue

            r = extract_result(stdout_i)
            if r is not None:
                results.append(r)

        except:
            continue

    # 4. Output existence (any successful run)
    if len(results) > 0:
        score += 0.2

    # 5. Stability via consensus (majority agreement)
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
    count = 0
    for line in output.split("\n"):
        if "Attempt" in line:
            count += 1
    return max(count, 1)


# -----------------------------
# RESET TEST DIR
# -----------------------------
def reset_test_dir(case_path):
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

    shutil.copytree(case_path, TEST_DIR)

    # Remove compiled .class files
    for file in os.listdir(TEST_DIR):
        if file.endswith(".class"):
            os.remove(os.path.join(TEST_DIR, file))


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

        stdout, stderr, duration = run_agent()

        print(stdout)

        score = evaluate(stdout, stderr)
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
    if TOTAL == 0:
        return

    avg_score = sum(SCORES) / len(SCORES)
    avg_attempts = sum(ATTEMPTS) / len(ATTEMPTS)
    avg_time = sum(TIMES) / len(TIMES)
    success_rate = (SUCCESS / TOTAL) * 100

    print("\n===== BENCHMARK RESULTS =====")
    print(f"Total Cases: {TOTAL}")
    print(f"Solved (score>=0.7): {SUCCESS}")
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"Avg Score: {avg_score:.2f}")
    print(f"Avg Attempts: {avg_attempts:.2f}")
    print(f"Avg Time: {avg_time:.2f} sec")


# -----------------------------
# ENTRY
# -----------------------------
if __name__ == "__main__":
    run_benchmark()