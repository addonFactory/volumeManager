from typing import TYPE_CHECKING

from pycaw.callbacks import MMNotificationClient

if TYPE_CHECKING:
    from . import GlobalPlugin


class NotificationCallback(MMNotificationClient):
    def __init__(self, plugin: "GlobalPlugin"):
        self.plugin = plugin

    def on_device_state_changed(self, device_id, new_state, new_state_id):
        self.plugin.fetchDevices()
