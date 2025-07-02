import os
import shutil

# Folders to check
folders = ['_includes', '_portfolio', '_publications', '_sass', '_assets']

# File extensions to check for references (add more if needed)
search_extensions = ('.html', '.md', '.scss', '.css', '.js', '.yml', '.yaml', '.json')

# Backup folder for unreferenced files
backup_root = 'unreferenced_backup'

# Collect all project files to search in
project_files = []
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith(search_extensions):
            project_files.append(os.path.join(root, f))

# Find unreferenced files
unreferenced = []

for folder in folders:
    if not os.path.isdir(folder):
        continue
    for root, dirs, files in os.walk(folder):
        for f in files:
            file_path = os.path.join(root, f)
            referenced = False
            for pf in project_files:
                with open(pf, 'r', encoding='utf-8', errors='ignore') as file:
                    if f in file.read():
                        referenced = True
                        break
            if not referenced:
                unreferenced.append(file_path)

# Move unreferenced files to backup folder, preserving structure
for file_path in unreferenced:
    rel_path = os.path.relpath(file_path, '.')  # relative to project root
    backup_path = os.path.join(backup_root, rel_path)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.move(file_path, backup_path)
    print(f"Moved: {file_path} -> {backup_path}")

print("\nAll unreferenced files have been moved to the 'unreferenced_backup' folder.")
print("If you need to restore them, copy them back to their original locations.")