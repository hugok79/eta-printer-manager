import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify

# ─── Düzeltilen Satır ───
from src.locale_config import _

class NotificationManager:
    def __init__(self):
        # libnotify sistemini uygulama adıyla ilklendir
        Notify.init("eta-printer-manager")

    def notify(self, title, message):
        """Yerel Pardus/Debian bildirim balonunu tetikler"""
        notification = Notify.Notification.new(title, message, "printer")
        notification.show()