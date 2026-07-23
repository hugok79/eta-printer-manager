import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

# Modülleri 'src' ve 'ui' altından çağırıyoruz
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