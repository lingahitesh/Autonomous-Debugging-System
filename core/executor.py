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