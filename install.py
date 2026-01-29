import os
import shutil
import json
import xml.etree.ElementTree as ET
import sys
import datetime

# --- Defaults (Used if install_config.json is missing) ---
DEFAULT_CONFIG = {
    "json": {
        "*": { "append_keys": ["objectSpawnersArr", "playerRestrictedAreaFiles", "Triggers"] }
    },
    "xml": {
        "cfgweather.xml": { "strategy": "settings" },
        "cfggameplay.xml": { "strategy": "settings" },
        "economycore.xml": { "strategy": "settings" },
        "*": { "strategy": "collection", "id_attributes": ["name", "pos", "color"] }
    }
}

# --- Config Loader ---
def load_config():
    if os.path.exists("install_config.json"):
        try:
            with open("install_config.json", "r") as f:
                print("Loaded custom install_config.json")
                return json.load(f)
        except Exception as e:
            print(f"Error loading install_config.json: {e}")
    return DEFAULT_CONFIG

def get_file_config(config, filename, file_type):
    """Retrives rules for a specific file, falling back to '*' wildcard."""
    section = config.get(file_type, {})
    # Check exact match
    if filename in section: return section[filename]
    # Check path match (if filename is a relative path)
    for key in section:
        if filename.endswith(key) or key.endswith(filename):
            return section[key]
    # Return wildcard
    return section.get("*", {})

# --- Helper Functions ---
def find_mission_data_folder():
    exclusions = {".git", ".github", "__pycache__", ".idea", ".vscode"}
    candidates = []
    for item in os.listdir("."):
        if os.path.isdir(item) and item not in exclusions:
            if item.startswith("dayzOffline"): candidates.append(item)
    if not candidates:
        for item in os.listdir("."):
             if os.path.isdir(item) and item not in exclusions: candidates.append(item)
    if not candidates:
        print("Error: No mission data folder found.")
        sys.exit(1)
    candidates.sort(key=lambda x: not x.startswith("dayzOffline"))
    return candidates[0]

def get_mission_path(mission_name):
    print("\n--- Mission Selection ---")
    print(f"Detected mod data for: {mission_name}")
    print("Enter server mission directory path:")
    path = input("Path: ").strip().replace('"', '')
    if not os.path.isdir(path):
        print(f"Error: Directory '{path}' not found.")
        sys.exit(1)
    return path

def create_backup(file_path):
    if os.path.exists(file_path):
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        try: shutil.copy2(file_path, f"{file_path}.{ts}.bak")
        except: pass

# --- Merge Logic ---
def deep_merge_json(target, source, append_keys):
    for key, value in source.items():
        if key in target:
            if isinstance(target[key], dict) and isinstance(value, dict):
                deep_merge_json(target[key], value, append_keys)
            elif isinstance(target[key], list) and isinstance(value, list):
                if key in append_keys:
                    for item in value:
                        if item not in target[key]: target[key].append(item)
                else:
                    target[key] = value # Overwrite
            else:
                target[key] = value # Overwrite
        else:
            target[key] = value
    return target

def get_node_id(node, strategy, id_attrs):
    if strategy == "settings": return node.tag.lower()

    # Collection: Generate ID based on specific attributes
    # If no attributes defined in config, try to guess common ones
    parts = [node.tag.lower()]
    found_attr = False

    # Check for configured attributes
    if id_attrs:
        for attr in id_attrs:
            if attr in node.attrib:
                parts.append(f"{attr}={node.attrib[attr]}")
                found_attr = True

    # If we didn't match any configured attributes, fall back to "All Attributes"
    # This handles complex nodes without names
    if not found_attr:
        for k, v in sorted(node.attrib.items()):
            parts.append(f"{k}={v}")

    return "|".join(parts)

def recursive_xml_merge(target, source, strategy, id_attrs):
    target_map = {}
    for child in target:
        ident = get_node_id(child, strategy, id_attrs)
        target_map[ident] = child

    for child in source:
        ident = get_node_id(child, strategy, id_attrs)
        if ident in target_map:
            target_child = target_map[ident]
            target_child.attrib.update(child.attrib)
            if child.text and child.text.strip():
                target_child.text = child.text
            recursive_xml_merge(target_child, child, strategy, id_attrs)
        else:
            target.append(child)

# --- Main Logic ---
def process_directory(source_root, target_root, config):
    for root, dirs, files in os.walk(source_root):
        rel_path = os.path.relpath(root, source_root)
        if rel_path == ".": rel_path = ""
        target_dir = os.path.join(target_root, rel_path)

        for d in dirs:
            if not os.path.exists(os.path.join(target_dir, d)): os.makedirs(os.path.join(target_dir, d))

        for filename in files:
            src = os.path.join(root, filename)
            dst = os.path.join(target_dir, filename)
            disp = os.path.join(rel_path, filename)

            # Use relative path for config lookup to allow folder-specific rules
            file_key = disp.replace("\\", "/")

            if not os.path.exists(dst):
                shutil.copy(src, dst)
                print(f"  [NEW] {disp}")
                continue

            if filename.endswith(".json"):
                try:
                    rules = get_file_config(config, file_key, "json")
                    append_keys = rules.get("append_keys", [])

                    with open(dst, 'r', encoding='utf-8') as f: t_data = json.load(f)
                    with open(src, 'r', encoding='utf-8') as f: s_data = json.load(f)

                    deep_merge_json(t_data, s_data, append_keys)
                    create_backup(dst)
                    with open(dst, 'w', encoding='utf-8') as f: json.dump(t_data, f, indent=4)
                    print(f"  [MERGED] {disp}")
                except Exception as e: print(f"  [ERROR] {disp}: {e}")

            elif filename.endswith(".xml"):
                try:
                    rules = get_file_config(config, file_key, "xml")
                    strategy = rules.get("strategy", "collection")
                    id_attrs = rules.get("id_attributes", ["name", "pos", "color"])

                    ET.register_namespace('', "")
                    t_tree = ET.parse(dst)
                    s_tree = ET.parse(src)

                    recursive_xml_merge(t_tree.getroot(), s_tree.getroot(), strategy, id_attrs)
                    create_backup(dst)

                    # Pretty Print Hack
                    def indent(elem, level=0):
                        i = "\n" + level * "    "
                        if len(elem):
                            if not elem.text or not elem.text.strip(): elem.text = i + "    "
                            if not elem.tail or not elem.tail.strip(): elem.tail = i
                            for elem in elem: indent(elem, level + 1)
                            if not elem.tail or not elem.tail.strip(): elem.tail = i
                        else:
                            if level and (not elem.tail or not elem.tail.strip()): elem.tail = i
                    indent(t_tree.getroot())

                    t_tree.write(dst, encoding="UTF-8", xml_declaration=True)
                    print(f"  [MERGED] {disp} (Strategy: {strategy})")
                except Exception as e: print(f"  [ERROR] {disp}: {e}")

            else:
                create_backup(dst)
                shutil.copy(src, dst)
                print(f"  [UPDATED] {disp}")

def main():
    print("=== Universal DayZ Mod Installer ===")
    config = load_config()
    data_dir = find_mission_data_folder()
    mission_path = get_mission_path(data_dir)
    print(f"\nScanning {data_dir}...")
    process_directory(data_dir, mission_path, config)
    print("\n=== Installation Complete ===")

if __name__ == "__main__":
    main()