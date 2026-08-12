import gi
gi.require_version('Gtk', '3.0')
import subprocess
import threading  
from gi.repository import Gtk, GLib  
from src.logger import logger
from src.locale_config import _

# Brand / Model -> Debian Package Mapping
DRIVER_PACKAGE_MAP = {
    "brother": "printer-driver-brlaser",
    "hp": "hplip",
    "epson": "printer-driver-escpr",
    "canon": "printer-driver-c2esp",
    "samsung": "printer-driver-splix",
    "xerox": "printer-driver-splix",
    "lexmark": "printer-driver-gutenprint",
    "kyocera": "printer-driver-gutenprint"
}

class DynamicDriverInstaller:
    """Checks missing printer driver packages and installs them on-demand via apt/pkexec."""

    @staticmethod
    def is_package_installed(package_name: str) -> bool:
        """Checks if a debian package is installed on the system."""
        try:
            res = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", package_name],
                capture_output=True,
                text=True
            )
            return "install ok installed" in res.stdout
        except Exception as e:
            logger.error(f"Error checking status for package {package_name}: {e}")
            return False

    @staticmethod
    def get_required_packages(make_and_model: str) -> list:
        """Determines all required driver packages based on printer brand keywords in string."""
        if not make_and_model:
            return []
        
        make_model_lower = make_and_model.lower()
        required_pkgs = []

        for brand, pkg in DRIVER_PACKAGE_MAP.items():
            if brand in make_model_lower and pkg not in required_pkgs:
                required_pkgs.append(pkg)
                
        return required_pkgs

    @classmethod
    def check_and_install_driver(cls, parent_window, make_and_model: str) -> bool:
        """Prompts user via GTK3 dialog and installs missing packages in a background thread with a non-blocking spinner."""
        required_pkgs = cls.get_required_packages(make_and_model)
        missing_pkgs = [pkg for pkg in required_pkgs if not cls.is_package_installed(pkg)]

        if not missing_pkgs:
            return True

        top_win = parent_window
        if hasattr(parent_window, 'get_toplevel'):
            top_win = parent_window.get_toplevel()
        if not isinstance(top_win, Gtk.Window):
            top_win = None

        pkgs_str = ", ".join(missing_pkgs)

        # 1. User Confirmation Dialog
        dialog = Gtk.MessageDialog(
            transient_for=top_win,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Driver Package Required")
        )
        dialog.format_secondary_text(
            _("The following package(s) are required for '{0}':\n\n{1}\n\nDo you want to install them now?").format(make_and_model, pkgs_str)
        )

        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.YES:
            logger.info("Driver installation cancelled by user.")
            return False

        # 2. Create Progress Dialog with Spinner
        prog_dialog = Gtk.Dialog(
            title=_("Installing Driver..."),
            transient_for=top_win,
            flags=Gtk.DialogFlags.MODAL
        )
        prog_dialog.set_default_size(320, 120)
        prog_dialog.set_deletable(False)

        box = prog_dialog.get_content_area()
        box.set_spacing(12)
        box.set_border_width(20)

        label = Gtk.Label(label=_("Downloading and installing required driver package(s),\nplease wait..."))
        spinner = Gtk.Spinner()

        box.pack_start(label, True, True, 0)
        box.pack_start(spinner, True, True, 0)

        prog_dialog.show_all()
        spinner.start()

        install_result = {"success": False}

        # 3. Background Thread Worker Function
        def install_worker():
            cmd = ["pkexec", "apt-get", "install", "-y"] + missing_pkgs
            try:
                logger.info(f"Installing missing driver package(s) '{pkgs_str}' via apt...")
                res = subprocess.run(cmd, check=True)
                install_result["success"] = (res.returncode == 0)
            except Exception as e:
                logger.error(f"Failed to install driver package(s) {pkgs_str}: {e}")
                install_result["success"] = False
            finally:
                GLib.idle_add(on_install_finished)

        # 4. Callback to Cleanup UI on Main Thread
        def on_install_finished():
            spinner.stop()
            prog_dialog.destroy()
            Gtk.main_quit()

        # Start Worker Thread
        thread = threading.Thread(target=install_worker, daemon=True)
        thread.start()

        # Keep GTK Event Loop Running (Prevents UI Freeze)
        Gtk.main()

        return install_result["success"]