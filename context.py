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