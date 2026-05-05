# Autonomous Multi-File Debugging Agent

An autonomous debugging system that continuously repairs broken programs through an execution-feedback loop.
Instead of generating one-shot fixes, the agent repeatedly:

Execute → Detect Failure → Localize Root Cause → Repair → Verify → Retry


The goal is not just generating code fixes, but identifying the actual root cause cross multiple files and safely applying corrections until the program behaves as intended.

## Structure

<pre>
Autonomous-Debugging-System/  
├── runner.py          # Main execution loop  
├── ai.py              # LLM fix generation + verification  
├── parser.py          # Compile/runtime error parsing  
├── fixer.py           # Patch parsing + code edits  
├── memory.py          # Local/global fix memory  
├── strategy.py        # Repair strategy selection  
├── scorer.py          # File prioritization  
├── context.py         # Multi-file traversal + context extraction  
├── test/              # Broken Java test cases  
└── README.md
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

* Python
* Java
* Groq API
* Git
* Subprocess execution
* Regex-based code analysis

## Current Capabilities

✔ Multi-file dependency traversal  
✔ Runtime + compile-time debugging  
✔ Recursive file prioritization  
✔ Incremental compilation  
✔ Fix verification  
✔ Memory-based repair reuse  
✔ Formatting-preserving patches  

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
