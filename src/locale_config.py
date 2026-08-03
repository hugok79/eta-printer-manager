import gettext
import locale
import os
import ctypes

DOMAIN = "eta-printer-manager"
LOCALE_DIR = "/usr/share/locale"

# Development phase check for local directory
if not os.path.exists(os.path.join(LOCALE_DIR, "tr", "LC_MESSAGES", f"{DOMAIN}.mo")):
    LOCALE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "locale"))

try:
    locale.setlocale(locale.LC_ALL, "")
except Exception:
    pass

# 1. Python gettext setup
gettext.bindtextdomain(DOMAIN, LOCALE_DIR)
gettext.textdomain(DOMAIN)
lang = gettext.translation(DOMAIN, localedir=LOCALE_DIR, fallback=True)
_ = lang.gettext

# 2. C Library (GTK / Glade XML) bindtextdomain setup
try:
    libc = ctypes.cdll.LoadLibrary("libc.so.6")
    libc.bindtextdomain(DOMAIN.encode("utf-8"), LOCALE_DIR.encode("utf-8"))
    libc.bind_textdomain_codeset(DOMAIN.encode("utf-8"), "UTF-8".encode("utf-8"))
except Exception as e:
    print(f"C bindtextdomain error: {e}")