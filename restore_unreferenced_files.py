import os
import shutil

backup_root = 'unreferenced_backup'

for root, dirs, files in os.walk(backup_root):
    for f in files:
        backup_file_path = os.path.join(root, f)
        # Compute the original path by removing the backup_root prefix
        rel_path = os.path.relpath(backup_file_path, backup_root)
        original_path = os.path.join('.', rel_path)
        os.makedirs(os.path.dirname(original_path), exist_ok=True)
        shutil.move(backup_file_path, original_path)
        print(f"Restored: {backup_file_path} -> {original_path}")

print("\nAll files have been restored to their original locations.")