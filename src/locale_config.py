import gettext
import os
import locale

APP_NAME = "eta-printer-manager"
LOCALE_DIR = "/usr/share/locale"

# Development phase check for local directory
if not os.path.exists(LOCALE_DIR):
    LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "po")

try:
    # Set the system's current language
    locale.setlocale(locale.LC_ALL, "")
except Exception:
    pass

# gettext setup
lang = gettext.translation(APP_NAME, localedir=LOCALE_DIR, fallback=True)
_ = lang.gettext