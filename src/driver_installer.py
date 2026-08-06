import gi
gi.require_version('Gtk', '3.0')
import subprocess
from gi.repository import Gtk
from src.logger import logger
from src.locale_config import _

# Brand / Model -> Debian Package Mapping
DRIVER_PACKAGE_MAP = {
    "brother": "printer-driver-brlaser",
    "hp": "hplip",
    "epson": "printer-driver-escpr",
    "canon": "printer-driver-c2esp",
    "samsung": "printer-driver-splix"
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
    def get_required_package(make_and_model: str) -> str:
        """Determines required driver package based on printer brand."""
        if not make_and_model:
            return None
        make_model_lower = make_and_model.lower()
        for brand, pkg in DRIVER_PACKAGE_MAP.items():
            if brand in make_model_lower:
                return pkg
        return None

    @classmethod
    def check_and_install_driver(cls, parent_window, make_and_model: str) -> bool:
        """Prompts the user via GTK3 dialog on main thread and installs missing package safely via apt."""
        # 1. Yazıcı isminden Debian paket adını bul (Örn: "Brother HL-L2300D" -> "printer-driver-brlaser")
        pkg_name = cls.get_required_package(make_and_model)

        # Sürücü paketi haritada yoksa veya zaten yüklüyse kuruluma gerek yok
        if not pkg_name or cls.is_package_installed(pkg_name):
            return True

        # 2. GTK3 Onay Penceresini Aç
        parent_widget = parent_window.window if hasattr(parent_window, 'window') else parent_window
        dialog = Gtk.MessageDialog(
            transient_for=parent_widget,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Driver Package Required")
        )
        dialog.format_secondary_text(
            _("The package '{0}' is required for '{1}'.\n\nDo you want to install it now?").format(pkg_name, make_and_model)
        )

        response = dialog.run()
        dialog.destroy()

        # 3. Kullanıcı Onay Verdiyse Gerçek Debian Paketini Kur
        if response == Gtk.ResponseType.YES:
            cmd = ["pkexec", "apt-get", "install", "-y", pkg_name]
            try:
                logger.info(f"Installing missing driver package '{pkg_name}' via apt...")
                res = subprocess.run(cmd, check=True)
                return res.returncode == 0
            except Exception as e:
                logger.error(f"Failed to install driver package {pkg_name}: {e}")
                return False

        return False