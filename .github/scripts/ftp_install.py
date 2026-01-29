import os
import json
import ftplib
import xml.etree.ElementTree as ET
import sys
import io
import datetime

# --- Helper Functions ---
def find_mission_data_folder():
    exclusions = {".git", ".github", "__pycache__", ".idea", ".vscode"}
    candidates = []
    for item in os.listdir("."):
        if os.path.isdir(item) and item not in exclusions:
            if item.startswith("dayzOffline"):
                candidates.append(item)
    if not candidates:
        for item in os.listdir("."):
             if os.path.isdir(item) and item not in exclusions:
                 candidates.append(item)
    if not candidates: return None
    candidates.sort(key=lambda x: not x.startswith("dayzOffline"))
    return candidates[0]

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

def process_json_content(target_bytes, source_path):
    try:
        target_data = json.loads(target_bytes.decode('utf-8'))
        with open(source_path, 'r', encoding='utf-8') as f: source_data = json.load(f)
        deep_merge_json(target_data, source_data)
        return json.dumps(target_data, indent=4).encode('utf-8')
    except: return None

def process_xml_content(target_bytes, source_path):
    try:
        ET.register_namespace('', "")
        target_tree = ET.ElementTree(ET.fromstring(target_bytes.decode('utf-8')))
        source_tree = ET.parse(source_path)

        changes = recursive_xml_merge(target_tree.getroot(), source_tree.getroot())

        if changes > 0:
            out = io.BytesIO()
            target_tree.write(out, encoding="UTF-8", xml_declaration=True)
            return out.getvalue()
        return None
    except Exception as e:
        print(f"XML Merge Error: {e}")
        return None

# --- FTP Logic ---
def run_ftp_install():
    # 1. Setup
    data_dir = find_mission_data_folder()
    if not data_dir:
        print("Error: Repo structure invalid. No mission data folder found.")
        sys.exit(1)

    HOST = os.environ.get("FTP_HOST")
    USER = os.environ.get("FTP_USER")
    PASS = os.environ.get("FTP_PASSWORD")
    PORT = int(os.environ.get("FTP_PORT", 21))
    PATH = os.environ.get("MISSION_PATH", "").strip()

    if not HOST or not USER or not PASS or not PATH:
        print("Error: Missing credentials or path.")
        sys.exit(1)

    print(f"Connecting to {HOST}...")
    try:
        ftp = ftplib.FTP()
        ftp.connect(HOST, PORT)
        ftp.login(USER, PASS)
        ftp.cwd(PATH)
        print(f"Connected to: {PATH}")

        # 2. Recursive Sync
        print(f"Syncing from local folder: {data_dir}")

        for root, dirs, files in os.walk(data_dir):
            rel_path = os.path.relpath(root, data_dir)
            if rel_path == ".": rel_path = ""

            ftp_path = rel_path.replace("\\", "/")

            if ftp_path:
                try: ftp.mkd(ftp_path)
                except: pass

            for fname in files:
                local_file = os.path.join(root, fname)
                remote_file_path = f"{ftp_path}/{fname}" if ftp_path else fname

                print(f"Processing {remote_file_path}...")

                exists_remotely = False
                try:
                    ftp.size(remote_file_path)
                    exists_remotely = True
                except: exists_remotely = False

                if not exists_remotely:
                    with open(local_file, "rb") as f:
                        ftp.storbinary(f"STOR {remote_file_path}", f)
                    print(f"  -> [NEW] Uploaded")
                    continue

                new_content = None
                if fname.endswith(".json") or fname.endswith(".xml"):
                    r = io.BytesIO()
                    ftp.retrbinary(f"RETR {remote_file_path}", r.write)
                    remote_content = r.getvalue()

                    if fname.endswith(".json"):
                        new_content = process_json_content(remote_content, local_file)
                    else:
                        new_content = process_xml_content(remote_content, local_file)

                # Generate Timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_name = f"{remote_file_path}.{timestamp}.bak"

                if new_content:
                    try:
                        ftp.rename(remote_file_path, backup_name)
                        print(f"  -> Backup created: {backup_name}")
                    except: pass

                    ftp.storbinary(f"STOR {remote_file_path}", io.BytesIO(new_content))
                    print(f"  -> [MERGED] Updated")

                elif (not fname.endswith(".json")) and (not fname.endswith(".xml")):
                    try:
                        ftp.rename(remote_file_path, backup_name)
                        print(f"  -> Backup created: {backup_name}")
                    except: pass

                    with open(local_file, "rb") as f:
                        ftp.storbinary(f"STOR {remote_file_path}", f)
                    print(f"  -> [OVERWRITTEN] Updated")
                else:
                    print(f"  -> No changes needed")

        ftp.quit()
        print("\n=== Success ===")

    except Exception as e:
        print(f"FTP Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_ftp_install()