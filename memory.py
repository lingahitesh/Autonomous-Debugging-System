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