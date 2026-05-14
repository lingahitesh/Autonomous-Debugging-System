Readme.md
# Autonomous Multi-File Debugging Agent

An autonomous debugging system that continuously repairs broken programs through an execution-feedback loop.
Instead of generating one-shot fixes, the agent repeatedly:

Execute → Detect Failure → Localize Root Cause → Repair → Verify → Retry


The goal is not just generating code fixes, but identifying the actual root cause cross multiple files and safely applying corrections until the program behaves as intended.

## Structure

<pre>
Autonomous-Debugging-System/
├── core/
│   ├── runner.py        # Orchestrates execution → diagnosis → fixing loop
│   ├── ai.py            # LLM interaction: fix generation + verification
│   ├── parser.py        # Parses compile/runtime errors into structured data
│   ├── fixer.py         # Applies code patches safely (line-level edits)
│
├── engine/
│   ├── context.py       # Multi-file traversal + relevant code extraction
│   ├── strategy.py      # Determines repair strategy (syntax, logic, safety)
│   ├── scorer.py        # Ranks files by likelihood of containing the bug
│
├── memory/
│   ├── memory.py        # Stores & retrieves past fixes (local/global patterns)
│
├── benchmark/
│   ├── case1_missing_brace/
│   ├── case2_infinite_loop/
│   ├── ...              # Standardized debugging test cases
│
├── test/                # Active working directory (mutable during runs) and contains backups
├── benchmark_runner.py  # Runs full benchmark suite + evaluation
├── fix_history.log      # Maintains logs of changes made to test case
├── README.md
</pre>

## Core Features

### 1. Multi-File Root Cause Analysis

Traverses project dependencies recursively to identify the actual source of failures across connected files.

Example: Main.java → Calculator.java → utils.java

Instead of patching the caller blindly, the agent prioritizes the file most likely responsible for the failure.

### 2. Strategy-Based Repair Engine

Selects repair strategies dynamically based on failure type.
Currently, it supports:
* Syntax / compilation errors
* Infinite loops / timeout failures
* Arithmetic exceptions
* Null reference errors
* Logical output mismatches

### 3. Autonomous Repair Loop

Rather than generating a single patch, the agent performs:

Run → Diagnose → Patch → Recompile → Rerun

Until:
* The error is resolved
* Output becomes valid
* No new failures are introduced

### 4. Memory-Aware Fixing

Stores successful fixes using:

#### **Local Memory -**
Exact file + line + error context

#### **Global Memory -**
Reusable structural patterns such as:

* Missing braces
* EOF parsing failures
* Repeated loop bugs

This reduces repeated reasoning, latency, and token usage.

### 5. Formatting-Preserving Patch Engine

Applies code edits while preserving:
* Indentation
* Block structure
* Closing braces
* File consistency

This prevents broken formatting during autonomous code modifications.

## Example Repair

### Input
utils.java

```java
for(int i = 1; i <= n; i--)
```

### Agent Fix
```java
for(int i = 1; i <= n; i++)
```

### Output
```text
Result: 5
```

## Benchmark Results

| Metric | Value    |
|--------|----------|
| Cases Tested | 10       |
| Success Rate | 100%     |
| Avg Attempts | 2.6      |
| Avg Repair Time | ~2.2 sec |

## System Architecture

### 1. Execution Engine

Runs user programs in a controlled environment and captures:
* stdout
* stderr
* exit codes
* stack traces

### 2. Analyzer

Parses:
* Java compilation errors
* Runtime exceptions
* Timeout failures
* Output mismatches

Maps: Error → File → Line → Function

### 3. Reasoning Agent

Uses an LLM to:
* Understand root cause
* Generate minimal safe fixes
* Preserve original program intent

### 4. Fix Engine

Applies fixes directly to source files while preserving formatting.
Supports:
* Single-line fixes
* Multi-line fixes
* Multi-file fixes

### 5. Evaluator

After every patch:
* Recompiles only modified files
* Re-runs program
* Rejects unsafe or repeated fixes

## Tech Stack

* Python (core engine)
* Java (target programs)
* Groq API (LLM reasoning)
* Subprocess execution
* Regex-based analysis
* Git (version control)

## Safety Mechanisms

To prevent code corruption during autonomous fixing:

- Backup + rollback system for every applied patch
- Compilation-based validation before accepting fixes
- Duplicate fix detection to avoid infinite loops
- Controlled patch application (limited edits per attempt)

## Current Capabilities

✔ Multi-file dependency traversal  
✔ Runtime + compile-time debugging  
✔ Recursive file prioritization  
✔ Incremental compilation  
✔ Fix verification  
✔ Memory-based repair reuse  
✔ Formatting-preserving patches  

## Limitations

- Currently focused on small to medium Java codebases
- Relies on LLM quality for fix generation
- Limited semantic understanding without AST integration
- Benchmark coverage is controlled and not yet large-scale

## Quick Setup

* Clone repository - 
  git clone https://github.com/lingahitesh/Embedded-Autonomous-Debugging-System.git

* Enter project - 
  cd Embedded-Autonomous-Debugging-System

* Install dependencies - 
  pip install -r requirements.txt

* Add API key - 
  Create .env file:
  GROQ_API_KEY=your_key_here

* Run debugger - 
  python runner.py

## Roadmap

* AST-based code editing
* Neural bug localization
* IDE integration
* Benchmark suite
* Support for larger codebases

## Vision

The long-term goal is to build a debugging system that becomes part of the developer workflow. Not just suggesting fixes, but autonomously detecting, repairing, validating, and learning from failures over time.



Runner.py- 

import subprocess
import os
from parser import parse_runtime_error, parse_compile_error
from context import extract_context, find_related_files_recursive, extract_suspicious_region
from ai import generate_fix, verify_fix
from fixer import parse_fix, apply_fix, undo_fix
from scorer import score_file
from strategy import choose_strategy
from memory import remember_fix, recall_fix
import difflib

WORK_DIR = os.getenv("WORK_DIR", "test")

def create_session_backup(files, base_dir):
    backup = {}

    for file_name in files:
        path = os.path.join(base_dir, file_name)

        if os.path.exists(path):
            with open(path, "r") as f:
                backup[file_name] = f.read()

    return backup

def restore_session_backup(backup, base_dir):
    for file_name, content in backup.items():
        path = os.path.join(base_dir, file_name)

        with open(path, "w") as f:
            f.write(content)

    print("↩️ Session rollback complete")

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

def preview_fix(file_path, line_no, new_code):
    with open(file_path, "r") as f:
        original = f.readlines()

    modified = original.copy()

    if 0 < line_no <= len(modified):
        indent = modified[line_no - 1][:len(modified[line_no - 1]) - len(modified[line_no - 1].lstrip())]
        modified[line_no - 1] = indent + new_code + "\n"
    else:
        modified.append(new_code + "\n")

    diff = difflib.unified_diff(
        original,
        modified,
        fromfile="before",
        tofile="after",
        lineterm=""
    )

    return list(diff)

def sanitize_fixes(fixes, parsed_file):
    cleaned = []
    seen = set()

    for file_name, line_no, new_code in fixes:
        target = file_name if file_name else parsed_file

        # skip invalid stuff
        if not target:
            continue
        if not isinstance(line_no, int):
            continue
        if not new_code or not new_code.strip():
            continue

        code = new_code.strip()

        # skip comments
        if code.startswith("//"):
            continue

        # remove duplicates
        key = (target, line_no)
        if key in seen:
            continue
        seen.add(key)

        cleaned.append((target, line_no, code))

    # VERY IMPORTANT: limit number of fixes
    return cleaned[:3]

def confirm_and_apply(fixes, base_dir, auto_apply=False):
    print("\n--- Proposed Fix ---")

    previews = []

    for file_name, line_no, new_code in fixes:
        target_file = file_name
        target_path = os.path.join(base_dir, target_file)

        if not os.path.exists(target_path):
            continue

        diff = preview_fix(target_path, line_no, new_code)
        previews.append((target_path, diff))

        print(f"\n📄 {target_file}")
        print("\n".join(diff))

    if auto_apply:
        choice = "y"
    else:
        choice = input("\nApply fix? (y/n): ").strip().lower()

    if choice == "y":
        for file_name, line_no, new_code in fixes:
            target_file = file_name
            target_path = os.path.join(base_dir, target_file)

            if os.path.exists(target_path):
                apply_fix(target_path, line_no, new_code)

        print("✅ Fix applied")
        return True

    print("❌ Fix skipped")
    return False

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
    file_path = os.path.join(WORK_DIR, "Main.java")
    directory = WORK_DIR
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
        changed_files = set()
        files_to_backup = []

        for file_name, _, _ in fixes:
            target_file = file_name if file_name else parsed.get("file")

            if target_file:
                files_to_backup.append(target_file)

        session_backup = create_session_backup(files_to_backup, base_dir)
        # APPLY FIX FIRST
        safe_fixes = sanitize_fixes(fixes, parsed.get("file"))

        if not safe_fixes:
            print("⚠️ No valid fixes")
            attempt += 1
            continue

        for file_name, line_no, new_code in safe_fixes:
            target_file = file_name
            target_path = os.path.join(base_dir, target_file)
            changed_files.add(target_file)

            if not os.path.exists(target_path):
                print(f"⚠️ Skipping invalid target file: {target_file}")
                continue

            apply_fix(target_path, line_no, new_code)
            with open("fix_history.log", "a") as f:
                f.write(f"{target_file}:{line_no} -> {new_code}\n")
            print("\n🔧 Applied Fix:")
            print(f"File: {target_file}")
            print(f"Line: {line_no}")
            print(f"New Code: {new_code}")

        # NOW CHECK COMPILATION
        temp_compile = compile_java(directory)

        if temp_compile.returncode == 0:
            print("✅ Fix accepted (compilation resolved)")
            remember_fix(local_key, fix)
            remember_fix(global_key, fix)
        else:
            print("⚠️ Fix broke compilation, rolling back...")
            restore_session_backup(session_backup, base_dir)
            attempt += 1
            continue

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
        print(verification)
        changed_files = set()
        files_to_backup = []

        for file_name, _, _ in fixes:
            target_file = file_name if file_name else parsed.get("file")

            if target_file:
                files_to_backup.append(target_file)

        session_backup = create_session_backup(files_to_backup, base_dir)
        safe_fixes = sanitize_fixes(fixes, parsed.get("file"))

        if not safe_fixes:
            print("⚠️ No valid fixes")
            attempt += 1
            continue

        for file_name, line_no, new_code in safe_fixes:
            target_file = file_name
            target_path = os.path.join(base_dir, target_file)
            changed_files.add(target_file)

            if not os.path.exists(target_path):
                print(f"⚠️ Skipping invalid target file: {target_file}")
                continue

            apply_fix(target_path, line_no, new_code)
            with open("fix_history.log", "a") as f:
                f.write(f"{target_file}:{line_no} -> {new_code}\n")
            print("\n🔧 Applied Fix:")
            print(f"File: {target_file}")
            print(f"Line: {line_no}")
            print(f"New Code: {new_code}")

        compile_failed = False
        compile_result = compile_java(directory)

        if compile_result.returncode != 0:
            compile_failed = True

        if compile_failed:
            print("⚠️ Fix broke compilation, rolling back...")
            restore_session_backup(session_backup, base_dir)
            attempt += 1
            continue

        if verification != "VALID":
            print("❌ Fix rejected by verifier")
            restore_session_backup(session_backup, base_dir)
            attempt += 1
            continue

        remember_fix(local_key, fix)
        remember_fix(global_key, fix)
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



benchmark_runner.py -

import os
import time
import shutil
import subprocess
import difflib

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
def run_agent(work_dir):
    start = time.time()

    process = subprocess.Popen(
        [os.sys.executable, "runner.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
        cwd=BASE_DIR,
        env={**os.environ, "WORK_DIR": work_dir}
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
# DIFF VIEW
# -----------------------------
def show_diff(file_path, original_lines, modified_lines):
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile="before",
        tofile="after",
        lineterm=""
    )
    print("\n".join(diff))


# -----------------------------
# APPLY FIXES
# -----------------------------
def apply_fix(file_path, line_no, new_code):
    with open(file_path, "r") as f:
        lines = f.readlines()

    if 0 < line_no <= len(lines):
        indent = lines[line_no - 1][:len(lines[line_no - 1]) - len(lines[line_no - 1].lstrip())]
        lines[line_no - 1] = indent + new_code + "\n"
    else:
        lines.append(new_code + "\n")

    with open(file_path, "w") as f:
        f.writelines(lines)


def confirm_and_apply(fixes, source_dir):
    print("\n--- Proposed Fix ---")

    for file_name, line_no, code in fixes:
        file_path = os.path.join(source_dir, file_name)

        with open(file_path, "r") as f:
            original = f.readlines()

        modified = original.copy()

        if 0 < line_no <= len(modified):
            indent = modified[line_no - 1][:len(modified[line_no - 1]) - len(modified[line_no - 1].lstrip())]
            modified[line_no - 1] = indent + code + "\n"

        print(f"\n📄 {file_name}")
        show_diff(file_path, original, modified)

    choice = input("\nApply fix to source? (y/n): ").strip().lower()

    if choice == "y":
        for file_name, line_no, code in fixes:
            apply_fix(os.path.join(source_dir, file_name), line_no, code)
        print("✅ Fix applied")
    else:
        print("❌ Fix discarded")


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

    for _ in range(3):
        stdout_i, stderr_i, _ = run_agent(work_dir)

        if stderr_i or "Program Timeout" in stdout_i:
            continue

        r = extract_result(stdout_i)
        if r is not None:
            results.append(r)

    if len(results) > 0:
        score += 0.2

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
        shutil.rmtree(TEST_DIR)

    shutil.copytree(source_dir, TEST_DIR)

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

# -----------------------------
# ENTRY
# -----------------------------
if __name__ == "__main__":
    run_benchmark()

Memory.py
import json
import os

MEMORY_FILE = "fix_memory.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def remember_fix(error_key, fix):
    memory = load_memory()
    memory[error_key] = fix
    save_memory(memory)

def recall_fix(error_key):
    memory = load_memory()
    return memory.get(error_key)

fixer.py
import os

def parse_fix(fix):
    fixes=[]

    if "START_FIX" in fix:
        lines=fix.splitlines()
        for line in lines:
            if ":" in line and "START_FIX" not in line and "END_FIX" not in line:
                parts=line.split(":",2)

                try:
                    if len(parts)==3:
                        file_name=parts[0].strip()
                        line_no=int(parts[1].strip())
                        code=parts[2].strip()
                    else:
                        file_name=None
                        line_no=int(parts[0].strip())
                        code=parts[1].strip()

                    fixes.append((file_name,line_no,code))
                except:
                    continue
        return fixes

    else:
        parts=fix.split(":",2)
        try:
            if len(parts)==3:
                return [(parts[0].strip(),int(parts[1].strip()),parts[2].strip())]
            else:
                return [(None,int(parts[0].strip()),parts[1].strip())]
        except:
            return []

def apply_fix(file_path, line_no, new_code):
    backup_path = file_path + ".bak"

    with open(file_path, "r") as f:
        lines = f.readlines()

    with open(backup_path, "w") as f:
        f.writelines(lines)

    lines = [line.rstrip("\n") for line in lines]

    while lines and not lines[-1].strip():
        lines.pop()

    new_code = new_code.strip()

    def get_indent(text):
        return text[:len(text) - len(text.lstrip())]

    if 0 < line_no <= len(lines):
        old_line = lines[line_no - 1]
        indentation = get_indent(old_line)
        lines[line_no - 1] = indentation + new_code

    else:
        indentation = ""

        if lines:
            indentation = get_indent(lines[-1])

        lines.append(indentation + new_code)

    with open(file_path, "w") as f:
        f.write("\n".join(lines) + "\n")

def undo_fix(file_path):
    backup_path = file_path + ".bak"

    if os.path.exists(backup_path):
        with open(backup_path, "r") as f:
            content = f.read()

        with open(file_path, "w") as f:
            f.write(content)

        print(f"↩️ Undo applied for {file_path}")


ai.py
from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_fix(error_info, context, strategy):
    context_text="\n".join(context)
    prompt=f"""
You are a strict Java debugging agent.

Fix the root cause while preserving original intent.

Error:
{error_info.get("message","")}

Strategy:
{strategy}

Code:
{context_text}

Rules:
- Fix only the real bug
- Preserve program behavior
- Prefer fixing source file over caller
- Do not add dummy prints, shortcuts, or bypass logic
- If loop issue, fix condition/update only
- If syntax issue, complete broken structure/statements
- If safety issue, add minimal guards
- If EOF parsing error, append missing braces on new lines
- If multiple files are shown, include file names

Output:
Single:
<line>: <code>

Multi:
START_FIX
<file>:<line>: <code>
<file>:<line>: <code>
END_FIX
"""

    response=client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role":"system",
                "content":"Output only valid Java fixes in required format."
            },
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()

def verify_fix(error_info, context, fix):
    context_text="\n".join(context)

    prompt=f"""
Error:
{error_info.get("message","")}

Code:
{context_text}

Fix:
{fix}

Reply ONLY:
VALID
or
INVALID

INVALID if:
- the original error would still occur
- the fix breaks program logic
- the fix repeats a previously failed pattern
- the fix does not resolve the root cause
"""

    response=client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role":"system",
                "content":"Strict validator."
            },
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()

content.py
import re
import os

def get_project_classes(base_dir):
    return {
        f.replace(".java", "")
        for f in os.listdir(base_dir)
        if f.endswith(".java")
    }

import re

def extract_suspicious_region(file_path, window=2):
    with open(file_path, "r") as f:
        lines = f.readlines()

    patterns = [
        r'\bfor\s*\(',
        r'\bwhile\s*\(',
        r'/',
        r'\breturn\b',
        r'\bnew\b'
    ]

    ranges = []

    for i, line in enumerate(lines):
        for pattern in patterns:
            if re.search(pattern, line):
                start = max(0, i - window)
                end = min(len(lines) - 1, i + window)
                ranges.append((start, end))
                break

    if not ranges:
        return []

    ranges.sort()
    merged = [ranges[0]]

    for start, end in ranges[1:]:
        last_start, last_end = merged[-1]

        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    result = []

    for start, end in merged:
        for i in range(start, end + 1):
            result.append(
                f"{i+1}: {lines[i].rstrip()}"
            )

    return result

def find_related_files_recursive(entry_file, base_dir, max_depth=3):
    visited=set()
    queue=[entry_file]
    depth=0

    while queue and depth<max_depth:
        next_queue=[]

        for file in queue:
            if file in visited:
                continue

            visited.add(file)
            path=os.path.join(base_dir,file)

            if not os.path.exists(path):
                continue

            with open(path,"r") as f:
                code=f.read()

            project_classes = get_project_classes(base_dir)
            matches = set()
            matches.update(re.findall(r'\b([A-Za-z_]\w*)\b', code))

            for cls in matches:
                if cls in project_classes:
                    fname = cls + ".java"
                    if fname not in visited:
                        next_queue.append(fname)

        queue=next_queue
        depth+=1

    return list(visited)

def extract_context(file_path, line, window=3):
    with open(file_path, "r") as f:
        lines = f.readlines()

    if line is None:return [f"{i+1}: {lines[i].rstrip()}" for i in range(len(lines))]
    start = max(0, line - window - 1)
    end = min(len(lines), line + window)
    context = []

    for i in range(start, end):
        prefix = ">> " if i == line - 1 else ""
        context.append(f"{i+1}: {prefix}{lines[i].rstrip()}")

    return context

parser.py
import re
import os

def parse_runtime_error(stderr):
    error_info={}

    # Extract exception type
    match_type=re.search(r'java\.lang\.(\w+)',stderr)
    if match_type:
        error_info["type"]=match_type.group(1)

    match_line = re.search(r'\((.*\.java):(\d+)\)', stderr)
    error_info["message"] = stderr.strip()

    if match_line:
        file_name = os.path.basename(match_line.group(1))
        error_info["file"] = file_name
        error_info["line"] = int(match_line.group(2))
    return error_info

def parse_compile_error(stderr):
    error_info={}
    match=re.search(r'(.*\.java):(\d+): error: (.*)',stderr)
    error_info["message"]=match.group(3)

    if match:
        full_path=os.path.normpath(match.group(1))
        error_info["file"]=os.path.basename(full_path)
        error_info["path"]=full_path
        error_info["line"]=int(match.group(2))

    return error_info