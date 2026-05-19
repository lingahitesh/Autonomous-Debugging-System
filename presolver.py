import re

def try_local_fix(parsed, file_path):
    """
    Attempts to fix known error patterns without calling the LLM.
    Returns (line_no, code) tuple if fixable, None otherwise.
    """
    message = parsed.get("message", "").lower()
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if any(m in message for m in ("end of file", "reached end", "'}' expected")):
        return _fix_missing_brace(lines)

    if "';' expected" in message:
        error_line = parsed.get("line")
        return _fix_missing_semicolon(lines, error_line)

    return None

def _fix_missing_brace(lines):
    """
    Scans the file and finds the first unclosed block,
    returns the insert position and the closing brace.
    """
    depth = 0
    last_open_line = 0
    block_end = None
    # Track depth and find where it goes negative or where
    # a return/statement appears at wrong depth
    clean = _strip_strings_and_comments(lines)
    scope_stack = []  # stack of line indices where { was opened

    for i, line in enumerate(clean):
        for ch in line:
            if ch == '{':
                scope_stack.append(i)
            elif ch == '}':
                if scope_stack:
                    scope_stack.pop()

    if not scope_stack:
        return None  # braces are balanced, not our problem
    # The last unclosed { — insert } after the next non-blank line
    last_unclosed = scope_stack[-1]  # 0-indexed line of the unclosed {
    # Find the line after which the block's content ends
    # Walk forward from last_unclosed, find last non-empty line
    # before either the next same-level statement or EOF
    insert_after = last_unclosed
    for i in range(last_unclosed + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("//"):
            insert_after = i

    insert_line_no = insert_after + 2  # 1-indexed, insert AFTER this line
    # Get indentation from the opening brace line
    open_line = lines[last_unclosed]
    indent = open_line[:len(open_line) - len(open_line.lstrip())]

    return (insert_line_no, indent + "}")

def _fix_missing_semicolon(lines, error_line):
    if not error_line or error_line > len(lines):
        return None
    line = lines[error_line - 1].rstrip()
    if not line.endswith(";") and not line.endswith("{") and not line.endswith("}"):
        return (error_line, line.strip() + ";")
    return None


def _strip_strings_and_comments(lines):
    """
    Returns lines with string literals and comments blanked out
    so brace counting isn't fooled by braces inside strings/comments.
    """
    clean = []
    in_block_comment = False

    for line in lines:
        result = []
        i = 0
        in_string = False
        in_char = False

        while i < len(line):
            c = line[i]

            if in_block_comment:
                if line[i:i+2] == '*/':
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if not in_string and not in_char:
                if line[i:i+2] == '//':
                    break  # rest of line is comment
                if line[i:i+2] == '/*':
                    in_block_comment = True
                    i += 2
                    continue
                if c == '"':
                    in_string = True
                    i += 1
                    continue
                if c == "'":
                    in_char = True
                    i += 1
                    continue
                result.append(c)
            else:
                if in_string and c == '\\':
                    i += 2
                    continue
                if in_string and c == '"':
                    in_string = False
                elif in_char and c == '\\':
                    i += 2
                    continue
                elif in_char and c == "'":
                    in_char = False
            i += 1
        clean.append("".join(result))

    return clean