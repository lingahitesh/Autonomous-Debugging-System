import os
from benchmark_runner import show_diff

# -----------------------------
# APPLY FIXES
# -----------------------------
def apply_fix(file_path, line_no, new_code):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if 0 < line_no <= len(lines):
        indent = lines[line_no - 1][:len(lines[line_no - 1]) - len(lines[line_no - 1].lstrip())] # Preserves user indentation
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