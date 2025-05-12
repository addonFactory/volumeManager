import logging

from pycaw.callbacks import MMNotificationClient

logger = logging.getLogger(__name__)


class NotificationCallback(MMNotificationClient):
    def __init__(self, callback):
        self.callback = callback

    def on_device_state_changed(self, device_id, new_state, new_state_id):
        try:
            self.callback()
        except Exception:
            logger.exception("Unhandeled exception in notification callback:")
