from pycaw.callbacks import MMNotificationClient


class NotificationCallback(MMNotificationClient):
    def __init__(self, callback):
        self.callback = callback

    def on_device_state_changed(self, device_id, new_state, new_state_id):
        self.callback()
