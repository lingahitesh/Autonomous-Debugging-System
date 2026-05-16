import os

def create_session_backup(files, base_dir):
    backup = {}

    for file_name in files:
        path = os.path.join(base_dir, file_name)

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                backup[file_name] = f.read()

    return backup

def restore_session_backup(backup, base_dir):
    for file_name, content in backup.items():
        path = os.path.join(base_dir, file_name)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    print("↩️ Session rollback complete")
