import re
import os

def get_project_classes(base_dir):
    return {
        f.replace(".java", "")
        for f in os.listdir(base_dir)
        if f.endswith(".java")
    }

def extract_suspicious_region(file_path, window=4):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    patterns = [
        r'\bfor\s*\(',
        r'\bwhile\s*\(',
        r'\breturn\b',
        r'\bnew\b',
        r'\bif\s*\(',
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
            result.append(f"{i+1}: {lines[i].rstrip()}")

    return result

def find_related_files_recursive(entry_file, base_dir, max_depth=3):
    visited = set()
    queue = [entry_file]
    depth = 0
    project_classes = get_project_classes(base_dir)

    while queue and depth < max_depth:
        next_queue = []

        for file in queue:
            if file in visited:
                continue

            visited.add(file)
            path = os.path.join(base_dir, file)

            if not os.path.exists(path):
                continue

            with open(path, "r", encoding="utf-8") as f:
                code = f.read()

            matches = set()
            matches.update(re.findall(r'\b([A-Za-z_]\w*)\b', code))

            for cls in matches:
                if cls in project_classes:
                    fname = cls + ".java"
                    if fname not in visited:
                        next_queue.append(fname)

        queue = next_queue
        depth += 1

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

def extract_method_context(file_path, line):
    """
    Extracts only the method containing the given line.
    Falls back to full file if method boundaries can't be found.
    Much cheaper than full file for LLM calls.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if line is None or line > len(lines):
        return [f"{i+1}: {lines[i].rstrip()}" for i in range(len(lines))]

    target = line - 1  # 0-indexed

    # Walk backward to find method signature
    method_start = target
    for i in range(target, -1, -1):
        stripped = lines[i].strip()
        # method signature heuristic: return type + name + parens
        if re.search(r'(public|private|protected|static|\s)\s+\w+\s+\w+\s*\(', lines[i]):
            method_start = i
            break

    # Walk forward to find method closing brace (balanced)
    depth = 0
    method_end = len(lines) - 1
    for i in range(method_start, len(lines)):
        for ch in lines[i]:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
        if depth == 0 and i >= method_start:
            method_end = i
            break

    return [f"{i+1}: {lines[i].rstrip()}" for i in range(method_start, method_end + 1)]