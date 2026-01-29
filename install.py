import os
import shutil
import json
import xml.etree.ElementTree as ET
import sys
import datetime

# --- Configuration ---
def find_mission_data_folder():
    """Scans for the mission data folder in the repo."""
    exclusions = {".git", ".github", "__pycache__", ".idea", ".vscode"}
    candidates = []

    # 1. Look for 'dayzOffline'
    for item in os.listdir("."):
        if os.path.isdir(item) and item not in exclusions:
            if item.startswith("dayzOffline"):
                candidates.append(item)

    # 2. Fallback
    if not candidates:
        for item in os.listdir("."):
             if os.path.isdir(item) and item not in exclusions:
                 candidates.append(item)

    if not candidates:
        print("Error: Could not find a mission data folder.")
        sys.exit(1)

    candidates.sort(key=lambda x: not x.startswith("dayzOffline"))
    return candidates[0]

def get_mission_path(mission_name):
    print("\n--- Mission Selection ---")
    print(f"Detected mod data for: {mission_name}")
    print("Enter the full path to your server's mission directory.")
    path = input("Path: ").strip()
    if path.startswith('"') and path.endswith('"'): path = path[1:-1]
    if not os.path.isdir(path):
        print(f"Error: Directory '{path}' not found.")
        sys.exit(1)
    return path

def create_backup(file_path):
    """Creates a timestamped .bak copy of the target file."""
    if os.path.exists(file_path):
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{file_path}.{timestamp}.bak"
        try:
            shutil.copy2(file_path, backup_path)
            print(f"  [BACKUP] Created {os.path.basename(backup_path)}")
        except Exception as e:
            print(f"  [WARNING] Failed to create backup: {e}")

# --- JSON Logic ---
def deep_merge_json(target, source):
    for key, value in source.items():
        if key in target:
            if isinstance(target[key], dict) and isinstance(value, dict):
                deep_merge_json(target[key], value)
            elif isinstance(target[key], list) and isinstance(value, list):
                for item in value:
                    if item not in target[key]:
                        target[key].append(item)
            else:
                target[key] = value
        else:
            target[key] = value
    return target

# --- XML Logic ---
def get_node_signature(node):
    """Generates unique ID from Tag + Attributes"""
    parts = [node.tag]
    for k, v in sorted(node.attrib.items()):
        parts.append(f"{k}:{v}")
    return "|".join(parts)

def recursive_xml_merge(target_parent, source_parent):
    changes = 0
    target_map = {}

    # Index Target
    for child in target_parent:
        sig = get_node_signature(child)
        if sig not in target_map:
            target_map[sig] = child

    # Merge Source
    for source_child in source_parent:
        sig = get_node_signature(source_child)

        if sig in target_map:
            target_child = target_map[sig]
            # Update Text
            if source_child.text and source_child.text.strip():
                if target_child.text != source_child.text:
                    target_child.text = source_child.text
                    changes += 1
            # Recurse
            changes += recursive_xml_merge(target_child, source_child)
        else:
            target_parent.append(source_child)
            target_map[sig] = source_child
            changes += 1

    return changes

def indent(elem, level=0):
    i = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip(): elem.text = i + "    "
        if not elem.tail or not elem.tail.strip(): elem.tail = i
        for elem in elem: indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip(): elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()): elem.tail = i

# --- Main Process ---
def process_directory(source_root, target_root):
    for root, dirs, files in os.walk(source_root):
        rel_path = os.path.relpath(root, source_root)
        if rel_path == ".": rel_path = ""

        target_dir = os.path.join(target_root, rel_path)

        # Ensure directories
        for d in dirs:
            dst_d = os.path.join(target_dir, d)
            if not os.path.exists(dst_d):
                os.makedirs(dst_d)
                print(f"Created directory: {os.path.join(rel_path, d)}")

        for filename in files:
            src_file = os.path.join(root, filename)
            dst_file = os.path.join(target_dir, filename)
            display_path = os.path.join(rel_path, filename)

            if not os.path.exists(dst_file):
                shutil.copy(src_file, dst_file)
                print(f"  [NEW] {display_path}")
                continue

            if filename.endswith(".json"):
                try:
                    with open(dst_file, 'r', encoding='utf-8') as f: target_data = json.load(f)
                    with open(src_file, 'r', encoding='utf-8') as f: source_data = json.load(f)

                    deep_merge_json(target_data, source_data)

                    create_backup(dst_file)
                    with open(dst_file, 'w', encoding='utf-8') as f:
                        json.dump(target_data, f, indent=4)
                    print(f"  [MERGED] {display_path}")
                except Exception as e:
                    print(f"  [ERROR] {display_path}: {e}")

            elif filename.endswith(".xml"):
                try:
                    ET.register_namespace('', "")
                    target_tree = ET.parse(dst_file)
                    source_tree = ET.parse(src_file)

                    count = recursive_xml_merge(target_tree.getroot(), source_tree.getroot())

                    if count > 0:
                        create_backup(dst_file)
                        indent(target_tree.getroot())
                        target_tree.write(dst_file, encoding="UTF-8", xml_declaration=True)
                        print(f"  [MERGED] {display_path} ({count} updates)")
                    else:
                        print(f"  [CHECKED] {display_path} (No changes)")
                except Exception as e:
                    print(f"  [ERROR] {display_path}: {e}")

            else:
                create_backup(dst_file)
                shutil.copy(src_file, dst_file)
                print(f"  [UPDATED] {display_path}")

def main():
    print("=== Universal DayZ Mod Installer ===")
    data_dir = find_mission_data_folder()
    mission_path = get_mission_path(data_dir)

    print(f"\nScanning {data_dir}...")
    process_directory(data_dir, mission_path)

    print("\n=== Installation Complete ===")

if __name__ == "__main__":
    main()