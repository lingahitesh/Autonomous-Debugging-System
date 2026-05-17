import re
import os

def split_multi_class_file(file_path, work_dir):
    """
    Splits a .java file containing multiple top-level class definitions
    into separate files. Returns list of created file names, or empty list
    if not applicable.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    pattern = re.compile(
        r'(?:^|\n)((?:public\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements[\w\s,]+)?\s*\{)'
    )
    matches = list(pattern.finditer(source))

    if len(matches) <= 1:
        return []

    class_blocks = []
    for i, match in enumerate(matches):
        start = match.start() if match.start() == 0 else match.start() + 1
        class_name = match.group(2)
        body = _extract_balanced(source, source.index(match.group(1), match.start()))
        class_blocks.append((class_name, body))

    created = []
    for class_name, body in class_blocks:
        out_path = os.path.join(work_dir, f"{class_name}.java")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(body + "\n")
        created.append(f"{class_name}.java")
        print(f"Split: {class_name}.java")

    return created

def _extract_balanced(source, start):
    """Extract a brace-balanced block starting at `start`."""
    depth = 0
    i = start
    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False

    while i < len(source):
        c = source[i]

        if in_line_comment:
            if c == '\n':
                in_line_comment = False
        elif in_block_comment:
            if source[i:i+2] == '*/':
                in_block_comment = False
                i += 1
        elif in_string:
            if c == '\\':
                i += 1
            elif c == '"':
                in_string = False
        elif in_char:
            if c == '\\':
                i += 1
            elif c == "'":
                in_char = False
        else:
            if source[i:i+2] == '//':
                in_line_comment = True
                i += 1
            elif source[i:i+2] == '/*':
                in_block_comment = True
                i += 1
            elif c == '"':
                in_string = True
            elif c == "'":
                in_char = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return source[start:i+1]
        i += 1

    return source[start:]  # unbalanced — return all (EOF bug case)