import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load locale and translation configuration first
import src.locale_config

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

# Sets application name in system processes (task manager)
GLib.set_prgname("eta-printer-manager")
GLib.set_application_name("Printers and Scanners")

# Module imports
from src.cups_backend import CupsBackend
from ui.ui import MainWindow


def main():
    cups_backend = CupsBackend()

    win = MainWindow(cups_backend)
    win.show_all()

    Gtk.main()

if __name__ == "__main__":
    main()
