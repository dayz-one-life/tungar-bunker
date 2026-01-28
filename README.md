# Tungar Bunker - DayZ Custom Map Addition

This repository contains all the necessary files to add the custom "Tungar Bunker" to your DayZ Sakhal mission. You can install this modification automatically using the provided Python script or manually by editing your mission files.

## Prerequisites

* A DayZ Server with a Sakhal mission folder (e.g., `dayzOffline.sakhal`).
* **For Automatic Install:** Python 3.x installed on your system.

---

## Method 1: Automatic Installation (Recommended)

This method uses a Python script to automatically copy files and inject the necessary code into your mission configuration files.

### Steps

1.  **Download the Files:** Ensure all files from this repository (including `install_tungar_bunker.py`) are in the same folder on your computer.
2.  **Run the Script:** Open your terminal or command prompt in that folder and run:
    ```bash
    python install_tungar_bunker.py
    ```
3.  **Provide Mission Path:** When prompted, paste the full path to your server's mission directory (e.g., `C:\DayZServer\mpmissions\dayzOffline.sakhal`).

The script will automatically:
* Create a `custom` folder in your mission directory if it doesn't exist.
* Copy `tungar-bunker.json` and `tungar-bunker-pra.json` to that folder.
* Update `cfggameplay.json` to spawn the bunker objects and restrict the area.
* Add the necessary underground triggers to `cfgundergroundtriggers.json`.
* Add the required loot and map groups to `mapgrouppos.xml` and `mapgroupproto.xml`.

---

## Method 2: Manual Installation

If you prefer to install the mod manually, follow these steps strictly to ensure the bunker loads correctly.

### 1. Copy Custom Files
1.  Navigate to your mission folder (e.g., `dayzOffline.sakhal`).
2.  Create a folder named `custom` if it does not already exist.
3.  Copy the following files from this repository into `dayzOffline.sakhal/custom/`:
    * `tungar-bunker.json`
    * `tungar-bunker-pra.json`

### 2. Update `cfggameplay.json`
Open `cfggameplay.json` in your mission folder and make the following changes:

* **Object Spawners:** Locate the `"objectSpawnersArr"` array inside `"WorldsData"`. Add the path to the bunker JSON:
    ```json
    "objectSpawnersArr": [
        "./custom/tungar-bunker.json"
    ],
    ```
  *(Note: If the array already has entries, add a comma after the previous entry and add this new line).*

* **Restricted Areas:** Locate the `"playerRestrictedAreaFiles"` array inside `"WorldsData"`. Add the path to the PRA JSON:
    ```json
    "playerRestrictedAreaFiles": [
        "./custom/tungar-bunker-pra.json"
    ],
    ```


### 3. Update `cfgundergroundtriggers.json`
1.  Open `undergroundtrigger-entries.json` from this repository.
2.  Open `cfgundergroundtriggers.json` in your mission folder.
3.  Copy all trigger objects (the code between `{` and `}`) from the source file and paste them into the `"Triggers": [ ... ]` array in your mission file. Ensure valid JSON formatting (commas between objects).

### 4. Update `mapgrouppos.xml`
1.  Open `mapgrouppos-entries.xml` from this repository.
2.  Open `mapgrouppos.xml` in your mission folder.
3.  Copy all `<group ... />` lines from the source file and paste them inside the `<map>` tag of your mission file.

### 5. Update `mapgroupproto.xml`
1.  Open `mapgroupproto-entries.xml` from this repository.
2.  Open `mapgroupproto.xml` in your mission folder.
3.  Copy the entire group definitions (e.g., `<group name="Land_Underground_Storage_Barracks" ...> ... </group>`) from the source file.
4.  Paste them inside the `<prototype>` tag of your mission file.

---
**Installation Complete!** Restart your server to see the changes.