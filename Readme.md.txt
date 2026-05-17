-> core/runner.py-

from repair_loop import compile_phase, runtime_phase
from executor import run_java
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK_DIR = os.path.join(BASE_DIR, "test")

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

-> core/executor.py -

import subprocess
import os

def compile_single_java(java_file, directory):
    return subprocess.run(
        ["javac", java_file],
        capture_output=True,
        text=True,
        cwd=directory
    )

def compile_java(directory):
    java_files = []

    for file in os.listdir(directory):
        if file.endswith(".java"):
            java_files.append(file)

    return subprocess.run(
        ["javac"] + java_files,
        capture_output=True,
        text=True,
        cwd=directory
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

-> core/validator.py

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

    # limit number of fixes
    return cleaned[:3]

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
        except ValueError:
            return False

    return True

-> core/session.py-

import os

def create_session_backup(files, base_dir):
    backup = {}

    for file_name in files:
        path = os.path.join(base_dir, file_name)

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                backup[file_name] = f.read()

    return backup

def restore_session_backup(backup, base_dir):
    for file_name, content in backup.items():
        path = os.path.join(base_dir, file_name)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    print("↩️ Session rollback complete")


-> core/repair_loop.py

import os
from parser import parse_compile_error, parse_runtime_error
from context import extract_context, find_related_files_recursive, extract_suspicious_region
from ai import generate_fix, verify_fix
from fixer import parse_fix, apply_fix, cleanup_backup
from scorer import score_file
from strategy import choose_strategy
from memory import remember_fix, recall_fix
from executor import compile_java, run_java
from session import create_session_backup, restore_session_backup
from validator import sanitize_fixes, is_output_valid

MAX_ATTEMPTS = 5

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

def attempt_repair(parsed, context, base_dir, work_dir, seen_fixes):
    strategy = choose_strategy(parsed)
    local_key, global_key = build_error_keys(parsed, strategy)
    fix = recall_fix(local_key)
    failed_fixes = []

    if fix:
        candidate_fixes = [fix]
    else:
        candidate_fixes = []

    for _ in range(3):
        if not candidate_fixes:
            current_fix = generate_fix(parsed, context, strategy,list(set(failed_fixes)))
        else:
            current_fix = candidate_fixes.pop(0)

        normalized_fix = " ".join(current_fix.lower().split())
        signature = f"{local_key}:{normalized_fix}"

        if signature in seen_fixes:
            failed_fixes.append(current_fix)
            continue

        fixes = parse_fix(current_fix)

        if not fixes:
            continue

        safe_fixes = sanitize_fixes(fixes, parsed.get("file"))

        if not safe_fixes:
            continue

        verification = verify_fix(parsed, context, current_fix)
        seen_fixes.add(signature)

        if verification != "VALID":
            failed_fixes.append(current_fix)
            continue

        files_to_backup = list({
            file_name
            for file_name, _, _ in safe_fixes
        })

        backup = create_session_backup(files_to_backup, base_dir)

        try:
            for file_name, line_no, code in safe_fixes:
                file_path = os.path.join(base_dir, file_name)

                if not os.path.exists(file_path):
                    raise Exception("Invalid file target")

                apply_fix(file_path, line_no, code)
                print(f"Applied fix: {file_name}:{line_no}")

            compile_result = compile_java(work_dir)

            if compile_result.returncode != 0:
                raise RuntimeError("Compilation failed")

            for file_name, _, _ in safe_fixes:
                file_path = os.path.join(base_dir, file_name)
                cleanup_backup(file_path)

            remember_fix(local_key, current_fix)
            remember_fix(global_key, current_fix)

            return True
        except Exception:
            failed_fixes.append(current_fix)
            print("Rolling back bad fix...")
            restore_session_backup(backup, base_dir)

    print("No valid repair found")

    return False

def compile_phase(work_dir):
    file_path = os.path.join(work_dir,"Main.java")
    base_dir = os.path.dirname(file_path)
    attempt = 0
    seen_fixes = set()
    while attempt < MAX_ATTEMPTS:
        print(f"\n--- Compile Attempt {attempt + 1} ---")
        compile_result = compile_java(work_dir)
        if compile_result.returncode == 0:
            print("Compilation Successful")
            return True
        parsed = parse_compile_error(compile_result.stderr)
        if not parsed:
            return False
        message = parsed.get("message", "").lower()
        file_path = os.path.join(base_dir, parsed["file"])

        if "end of file" in message:
            context = extract_suspicious_region(file_path)

            if not context:
                context = extract_context(file_path, None)

        else:
            context = extract_context(file_path, parsed["line"])
        fixed = attempt_repair(parsed,context,base_dir,work_dir,seen_fixes)
        if not fixed:
            attempt += 1
            continue
        attempt += 1
    return False


def runtime_phase(work_dir, class_name):
    file_path = os.path.join(work_dir,"Main.java")
    base_dir = os.path.dirname(file_path)
    attempt = 0
    seen_fixes = set()
    while attempt < MAX_ATTEMPTS:
        print(f"\n--- Run Attempt {attempt + 1} ---")
        result = run_java(class_name,work_dir)

        if not result:
            return False
        if result.returncode == 0 and is_output_valid(result.stdout):
            print("Running Successful")
            return True
        if result.returncode == -1:
            parsed = {
                "message":"timeout",
                "file":"Main.java",
                "line":None
            }
        else:
            parsed = parse_runtime_error(result.stderr)
            if not parsed:
                parsed = {
                    "message":"output mismatch",
                    "file":"Main.java",
                    "line":None
                }
        entry_file = parsed.get("file")
        if not entry_file:
            entry_file = "Main.java"
        files = find_related_files_recursive(entry_file,base_dir)
        files = sorted(
            files,
            key=lambda f: score_file(f,entry_file),
            reverse=True
        )
        context = []
        for file in files:
            path = os.path.join(base_dir,file)
            context.append(f"\n--- {file} ---")
            region = extract_suspicious_region(path)
            if region:
                context += region
            else:
                context += extract_context(path,None)
        fixed = attempt_repair(parsed,context,base_dir,work_dir,seen_fixes)
        if not fixed:
            attempt += 1
            continue
        attempt += 1
    return False

-> benchmark_runner.py -

import os
import time
import shutil
import subprocess
import difflib
import sys
import json

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
        [sys.executable, os.path.join('core', 'runner.py')],
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
            except ValueError:
                return None
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
        lineterm=""
    )
    print("\n".join(diff))

# -----------------------------
# APPLY FIXES
# -----------------------------
def apply_fix(file_path, line_no, new_code):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if 0 < line_no <= len(lines):
        indent = lines[line_no - 1][:len(lines[line_no - 1]) - len(lines[line_no - 1].lstrip())]
        lines[line_no - 1] = indent + new_code + "\n"
    else:
        lines.append(new_code + "\n")

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def confirm_and_apply(fixes, source_dir):
    print("\n--- Proposed Fix ---")

    for file_name, line_no, code in fixes:
        file_path = os.path.join(source_dir, file_name)

        with open(file_path, "r", encoding="utf-8") as f:
            original = f.readlines()

        modified = original.copy()
        if 0 < line_no <= len(modified):
            indent = modified[line_no - 1][:len(modified[line_no - 1]) - len(modified[line_no - 1].lstrip())]
            modified[line_no - 1] = indent + code + "\n"

        print(f"\n📄 {file_name}")
        show_diff(original, modified)

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

    report = {
        "total": TOTAL,
        "success": SUCCESS,
        "success_rate": success_rate,
        "scores": SCORES,
        "attempts": ATTEMPTS,
        "times": TIMES
    }

    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

# -----------------------------
# ENTRY
# -----------------------------
if __name__ == "__main__":
    run_benchmark()

-> memory.py

import json
import os
import tempfile

MEMORY_FILE = "fix_memory.json"
MAX_MEMORY = 500

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError:
        return {}

def save_memory(memory):
    fd, temp_path = tempfile.mkstemp(suffix=".json")

    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

    os.replace(temp_path, MEMORY_FILE)

def remember_fix(error_key, fix):
    memory = load_memory()

    if error_key in memory:
        del memory[error_key]

    memory[error_key] = fix

    if len(memory) > MAX_MEMORY:
        oldest = list(memory.keys())[0]
        del memory[oldest]

    save_memory(memory)

def recall_fix(error_key):
    memory = load_memory()

    return memory.get(error_key)

-> fixer.py -

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
                except ValueError:
                    continue
        return fixes

    else:
        parts=fix.split(":",2)
        try:
            if len(parts)==3:
                return [(parts[0].strip(),int(parts[1].strip()),parts[2].strip())]
            else:
                return [(None,int(parts[0].strip()),parts[1].strip())]
        except ValueError:
            return []

def cleanup_backup(file_path):
    backup_path = file_path + ".bak"

    if os.path.exists(backup_path):
        os.remove(backup_path)

def apply_fix(file_path, line_no, new_code):
    backup_path = file_path + ".bak"

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(backup_path, "w", encoding="utf-8") as f:
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

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

-> ai.py -

from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_fix(error_info, context, strategy,failed_fixes=None):
    history = ""

    if failed_fixes:
        history = "\n".join(failed_fixes)
    print(history)
    context_text="\n".join(context)
    prompt=f"""
You are a strict Java debugging agent.

Fix the root cause while preserving original intent.

Error:
{error_info.get("message","")}

Failed history:
{history}

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

-> context.py -

import re
import os

def get_project_classes(base_dir):
    return {
        f.replace(".java", "")
        for f in os.listdir(base_dir)
        if f.endswith(".java")
    }

def extract_suspicious_region(file_path, window=2):
    with open(file_path, "r", encoding="utf-8") as f:
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
    project_classes = get_project_classes(base_dir)

    while queue and depth<max_depth:
        next_queue=[]

        for file in queue:
            if file in visited:
                continue

            visited.add(file)
            path=os.path.join(base_dir,file)

            if not os.path.exists(path):
                continue

            with open(path,"r", encoding="utf-8") as f:
                code=f.read()

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
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if line is None:
        return [f"{i+1}: {lines[i].rstrip()}" for i in range(len(lines))]
    start = max(0, line - window - 1)
    end = min(len(lines), line + window)
    context = []

    for i in range(start, end):
        prefix = ">> " if i == line - 1 else ""
        context.append(f"{i+1}: {prefix}{lines[i].rstrip()}")

    return context

-> parser.py -

import re
import os

def parse_runtime_error(stderr):
    error_info = {}
    match_type = re.search(r'java\.lang\.(\w+)', stderr)

    if match_type:
        error_info["type"] = match_type.group(1)

    match_line = re.search(r'\((.*\.java):(\d+)\)', stderr)
    error_info["message"] = stderr.strip()

    if match_line:
        file_name = os.path.basename(match_line.group(1))
        error_info["file"] = file_name
        error_info["line"] = int(match_line.group(2))

    return error_info

def parse_compile_error(stderr):
    match = re.search(r'(.*\.java):(\d+): error: (.*)', stderr)

    if not match:
        return None

    return {
        "file": os.path.basename(
            os.path.normpath(match.group(1))
        ),
        "path": os.path.normpath(
            match.group(1)
        ),
        "line": int(
            match.group(2)
        ),
        "message": match.group(3)
    }

I have a separate benchmark directory containing all test cases which I use for testing and and a directory test for storing the test codes temporarily. I have all other directories mentioned above in the codes. Please suggest modifications to the code or even give a file like this containing all the modified codes. Do as directed only and dont start making another UI or something. I'm unable to solve a code like the one pasted below

public class Main
{
    public static void main(String[] args)
    {
        int result = new Calculator().compute(10);
        System.out.println("Result: " + result);
    }
}

public class Calculator
{
    public int compute(int n)
    {
        utils helper = new utils();
        int sum = helper.sumToN(n);
        int avg = helper.average(sum, n);
        return avg;
    }
}

public class utils
{
    public int sumToN(int n)
    {
        int sum = 0;
        for(int i = 1; i <= n; i++)
        {
            sum += i;

        return sum;
    }

    public int average(int sum, int n)
    {
        return sum / n;
    }
}

Please suggest modifications to make my code more robust