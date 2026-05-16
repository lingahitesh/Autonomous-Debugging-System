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