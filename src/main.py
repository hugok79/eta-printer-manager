import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

# Sets application name in system processes (task manager)
GLib.set_prgname("eta-printer-manager")
GLib.set_application_name("Printers and Scanners")

# Module imports
from src.cups_backend import CupsBackend
from src.scanner_backend import ScannerBackend
from ui.ui import MainWindow



def main():
    # Initialize motors
    cups_backend = CupsBackend()
    scanner_backend = ScannerBackend()

    # Start main interface and inject motors
    win = MainWindow(cups_backend, scanner_backend)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()

    # GTK Main Loop
    Gtk.main()

if __name__ == "__main__":
    main()