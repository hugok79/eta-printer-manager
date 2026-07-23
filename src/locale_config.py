import gettext
import os
import locale

APP_NAME = "Pardus-Printers"
LOCALE_DIR = "/usr/share/locale"

# Geliştirme aşamasında yerel dizini de kontrol etmesi için
if not os.path.exists(LOCALE_DIR):
    LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "po")

try:
    # Sistemin mevcut dilini ayarla
    locale.setlocale(locale.LC_ALL, "")
except Exception:
    pass

# gettext kurulumu
lang = gettext.translation(APP_NAME, localedir=LOCALE_DIR, fallback=True)
_ = lang.gettext