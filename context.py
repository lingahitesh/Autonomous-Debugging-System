import re
import os

def get_project_classes(base_dir):
    return {
        f.replace(".java", "")
        for f in os.listdir(base_dir)
        if f.endswith(".java")
    }

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

            # capture all identifiers
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