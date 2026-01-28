import os
import shutil
import json
import xml.etree.ElementTree as ET

def get_mission_path():
    path = input("Enter the full path to your DayZ mission directory (e.g., C:\\DayZServer\\mpmissions\\dayzOffline.sakhal): ").strip()
    # Remove quotes if the user pasted them
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]

    if not os.path.isdir(path):
        print(f"Error: The directory '{path}' does not exist.")
        exit(1)

    return path

def install_custom_files(mission_path):
    print("\n--- Step 1: Copying custom files ---")
    custom_dir = os.path.join(mission_path, "custom")

    # Create custom folder if it doesn't exist
    if not os.path.exists(custom_dir):
        os.makedirs(custom_dir)
        print(f"Created directory: {custom_dir}")

    files_to_copy = ["tungar-bunker.json", "tungar-bunker-pra.json"]

    for filename in files_to_copy:
        if os.path.exists(filename):
            shutil.copy(filename, os.path.join(custom_dir, filename))
            print(f"Copied {filename} to {custom_dir}")
        else:
            print(f"Warning: Source file {filename} not found in current directory. Skipping copy.")

def update_cfggameplay(mission_path):
    print("\n--- Step 2 & 3: Updating cfggameplay.json ---")
    cfg_path = os.path.join(mission_path, "cfggameplay.json")

    if not os.path.exists(cfg_path):
        print(f"Error: {cfg_path} not found. Skipping.")
        return

    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Ensure WorldsData exists
        if "WorldsData" not in data:
            print("Error: 'WorldsData' block not found in cfggameplay.json.")
            return

        changed = False

        # Update objectSpawnersArr
        obj_spawners = data["WorldsData"].get("objectSpawnersArr", [])
        target_spawner = "./custom/tungar-bunker.json"
        if target_spawner not in obj_spawners:
            obj_spawners.append(target_spawner)
            data["WorldsData"]["objectSpawnersArr"] = obj_spawners
            print(f"Added {target_spawner} to objectSpawnersArr")
            changed = True
        else:
            print(f"Skipping: {target_spawner} already exists in objectSpawnersArr")

        # Update playerRestrictedAreaFiles
        pra_files = data["WorldsData"].get("playerRestrictedAreaFiles", [])
        target_pra = "./custom/tungar-bunker-pra.json"
        if target_pra not in pra_files:
            pra_files.append(target_pra)
            data["WorldsData"]["playerRestrictedAreaFiles"] = pra_files
            print(f"Added {target_pra} to playerRestrictedAreaFiles")
            changed = True
        else:
            print(f"Skipping: {target_pra} already exists in playerRestrictedAreaFiles")

        if changed:
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print("Successfully saved changes to cfggameplay.json")

    except json.JSONDecodeError as e:
        print(f"Error parsing cfggameplay.json: {e}")
    except Exception as e:
        print(f"An unexpected error occurred processing cfggameplay.json: {e}")

def update_underground_triggers(mission_path):
    print("\n--- Step 4: Updating cfgundergroundtriggers.json ---")
    trigger_path = os.path.join(mission_path, "cfgundergroundtriggers.json")
    source_file = "undergroundtrigger-entries.json"

    if not os.path.exists(trigger_path):
        print(f"Error: {trigger_path} not found.")
        return
    if not os.path.exists(source_file):
        print(f"Error: Source file {source_file} not found.")
        return

    try:
        with open(trigger_path, 'r', encoding='utf-8') as f:
            target_data = json.load(f)

        with open(source_file, 'r', encoding='utf-8') as f:
            source_data = json.load(f)

        if "Triggers" not in target_data:
            target_data["Triggers"] = []

        added_count = 0
        existing_triggers = target_data["Triggers"]

        for new_trigger in source_data.get("Triggers", []):
            # Duplicate check: simplistic check using strict equality
            # A more robust check might compare just Position and Size
            is_duplicate = False
            for existing in existing_triggers:
                if existing == new_trigger:
                    is_duplicate = True
                    break

            if not is_duplicate:
                existing_triggers.append(new_trigger)
                added_count += 1

        if added_count > 0:
            with open(trigger_path, 'w', encoding='utf-8') as f:
                json.dump(target_data, f, indent=4)
            print(f"Added {added_count} new triggers to cfgundergroundtriggers.json")
        else:
            print("No new triggers added (all entries appeared to be duplicates).")

    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}")

def update_mapgrouppos(mission_path):
    print("\n--- Step 5: Updating mapgrouppos.xml ---")
    xml_path = os.path.join(mission_path, "mapgrouppos.xml")
    source_file = "mapgrouppos-entries.xml"

    if not os.path.exists(xml_path) or not os.path.exists(source_file):
        print("Error: Target or Source XML file missing.")
        return

    try:
        ET.register_namespace('', "") # Prevents ns0: prefixes
        target_tree = ET.parse(xml_path)
        target_root = target_tree.getroot()

        source_tree = ET.parse(source_file)
        source_root = source_tree.getroot()

        # Build a set of existing (name, pos) tuples for fast lookup
        existing_entries = set()
        for group in target_root.findall("group"):
            name = group.get("name")
            pos = group.get("pos")
            if name and pos:
                existing_entries.add((name, pos))

        added_count = 0
        for group in source_root.findall("group"):
            name = group.get("name")
            pos = group.get("pos")

            if (name, pos) not in existing_entries:
                target_root.append(group)
                existing_entries.add((name, pos)) # Add to set to prevent internal duplicates in source
                added_count += 1

        if added_count > 0:
            # Indentation helper
            indent(target_root)
            target_tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
            print(f"Added {added_count} groups to mapgrouppos.xml")
        else:
            print("No new groups added to mapgrouppos.xml (duplicates found).")

    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")

def update_mapgroupproto(mission_path):
    print("\n--- Step 6: Updating mapgroupproto.xml ---")
    xml_path = os.path.join(mission_path, "mapgroupproto.xml")
    source_file = "mapgroupproto-entries.xml"

    if not os.path.exists(xml_path) or not os.path.exists(source_file):
        print("Error: Target or Source XML file missing.")
        return

    try:
        ET.register_namespace('', "")
        target_tree = ET.parse(xml_path)
        target_root = target_tree.getroot()

        source_tree = ET.parse(source_file)
        source_root = source_tree.getroot()

        # For proto, uniqueness is usually just the group name
        existing_names = set()
        for group in target_root.findall("group"):
            name = group.get("name")
            if name:
                existing_names.add(name)

        added_count = 0
        for group in source_root.findall("group"):
            name = group.get("name")

            if name not in existing_names:
                target_root.append(group)
                existing_names.add(name)
                added_count += 1
            else:
                # Optional: Warn if trying to add a duplicate definition
                pass

        if added_count > 0:
            indent(target_root)
            target_tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
            print(f"Added {added_count} groups to mapgroupproto.xml")
        else:
            print("No new groups added to mapgroupproto.xml (definitions already exist).")

    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")

def indent(elem, level=0):
    """Helper to pretty-print XML"""
    i = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def main():
    print("=== Tungar Bunker Install Script ===")
    mission_path = get_mission_path()

    install_custom_files(mission_path)
    update_cfggameplay(mission_path)
    update_underground_triggers(mission_path)
    update_mapgrouppos(mission_path)
    update_mapgroupproto(mission_path)

    print("\n=== Installation Complete ===")

if __name__ == "__main__":
    main()