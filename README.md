# ETA Printer Manager

## Overview
**ETA Printer Manager** is a GTK3-based printer and scanner management utility designed for Pardus and Debian-based Linux environments. It streamlines device setup, queue monitoring, and driver installation while proactively solving common Linux printing issues—such as devices defaulting to non-functional "Generic" drivers when required packages are missing.

## Features
* **Proactive Driver Installation:** Checks for required driver packages (e.g., `hplip`, `printer-driver-brlaser`) *before* registering the device with CUPS. If missing, it installs drivers via an embedded live terminal dialog, preventing the printer from being added as an unusable "Generic" device.
* **Native GTK3 Print Queue Window:** Replaces external browser-based CUPS management with a clean, fully integrated GTK3 print queue interface.
* **Smart Auto-Refresh:** Utilizes a non-blocking `GLib` timer (2-second interval) to perform delta updates on print jobs without clearing the treeview, eliminating screen flicker, preserving row selection, and keeping CPU/RAM consumption minimal.
* **Pure Native `pycups` Backend:** Interacts directly with the CUPS IPP API instead of executing shell `subprocess` commands (`lpstat`, `cancel`), providing faster execution and clean data parsing.
* **Human-Readable Job Details:** Formats raw Unix timestamps into `YYYY-MM-DD HH:MM:SS` strings, converts bytes into KB/MB, and reliably resolves originating user attributes.
* **Form Validation:** Validates IP addresses and URIs during manual printer setup to prevent invalid system configurations.

## Usage
* **Device Overview:** Launch the app to view all configured and discovered printers/scanners.
* **Print Queue:** Click **Open Queue** on any printer to monitor active print jobs in real-time or cancel specific jobs.
* **Driver Setup:** When adding a new printer, the app automatically prompts to install driver packages if missing and shows live progress inside an embedded terminal.

## Dependencies & Requirements
Ensure all required system dependencies and Python libraries are installed:

```bash
sudo apt update
sudo apt install python3-gi python3-cups gir1.2-gtk-3.0 gir1.2-vte-2.91 cups
Running the Application
Navigate to the project directory and run the application using Python's module flag:

Bash
cd pardus-printers
python3 -m src.main
Troubleshooting
CUPS Service Not Running: Ensure the CUPS service is active on your system:

Bash
sudo systemctl status cups
Driver Terminal Fails to Open: Ensure gir1.2-vte-2.91 is installed to support embedded VTE terminal dialogs.

Permission Issues: Package installation for missing drivers requires system administrator credentials via pkexec.

License
This project is licensed under the GPL v3 License. See the LICENSE file for more details.

Acknowledgments
pycups: For providing native Python bindings for the CUPS API.

PyGObject / GTK3: For the GUI framework.

VTE (Virtual Terminal Emulator): For embedded terminal rendering during driver installation.

CUPS: The standards-based printing system for Linux.