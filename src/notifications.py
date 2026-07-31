import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify
from src.locale_config import _

class NotificationManager:
    def __init__(self):
        # Initialize the libnotify system with the application name
        Notify.init("eta-printer-manager")

    def notify(self, title, message):
        """Triggers a local Pardus/Debian notification bubble"""
        notification = Notify.Notification.new(title, message, "printer")
        notification.show()