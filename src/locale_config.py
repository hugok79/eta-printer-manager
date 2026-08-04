import gettext
import locale
import os

DOMAIN = "eta-printer-manager"
LOCALE_DIR = "/usr/share/locale"

# Development phase check for local locale directory
local_locale = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "locale"))
if not os.path.exists(os.path.join(LOCALE_DIR, "tr", "LC_MESSAGES", f"{DOMAIN}.mo")) and os.path.exists(local_locale):
    LOCALE_DIR = local_locale

# Set system locale configuration
try:
    locale.setlocale(locale.LC_ALL, "")
except Exception:
    pass

# Notify underlying C library (GTK / Glade XML) using Python's standard locale module
if hasattr(locale, "bindtextdomain"):
    locale.bindtextdomain(DOMAIN, LOCALE_DIR)
    locale.bind_textdomain_codeset(DOMAIN, "UTF-8")

# Configure Python gettext bindings for _() function
gettext.bindtextdomain(DOMAIN, LOCALE_DIR)
gettext.textdomain(DOMAIN)

lang = gettext.translation(DOMAIN, localedir=LOCALE_DIR, fallback=True)
_ = lang.gettext