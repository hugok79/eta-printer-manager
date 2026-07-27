import sys
import os

# Kök dizini (/usr/share/pardus/eta-printer-manager) Python yoluna ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

# Modül importları
from src.cups_backend import CupsBackend
from src.scanner_backend import ScannerBackend
from ui.ui import MainWindow

def main():
    # Motorları ilklendir
    cups_backend = CupsBackend()
    scanner_backend = ScannerBackend()

    # Ana arayüzü başlat ve motorları enjekte et
    win = MainWindow(cups_backend, scanner_backend)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()

    # GTK Ana Döngüsü
    Gtk.main()

if __name__ == "__main__":
    main()