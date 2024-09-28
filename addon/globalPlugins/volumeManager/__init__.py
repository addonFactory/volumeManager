# VolumeManager NVDA addon
# Authors: Danstiv, Beqa gozalishvili
# Copyright 2019-2024, released under GPL.

import addonHandler
import globalPluginHandler
import gui
import tones
import ui
from pycaw.utils import AudioUtilities
from speech import cancelSpeech

from .audioManager import AudioManager
from .interface import ChangeVolumeDialog
from .notification_callback import NotificationCallback
from .utils import doc

addonHandler.initTranslation()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlayActive = False
        self.currentAppIndex = 0
        self.audioManager = AudioManager()
        self.initialize()
        self.currentApp = self.masterVolume
        self.baseGestures = {
            "kb:nvda+shift+v": "toggleOverlay",
            "kb:volumeDown": "onVolumeDown",
            "kb:volumeUp": "onVolumeUp",
        }
        self.overlayGestures = {
            "kb:leftArrow": "moveToPreviousApp",
            "kb:rightArrow": "moveToNextApp",
            "kb:downArrow": "decreaseVolume",
            "kb:upArrow": "increaseVolume",
            "kb:space": "setVolume",
            "kb:m": "muteApp",
        }
        self.setBaseGestures()
        self.deviceEnumerator = AudioUtilities.GetDeviceEnumerator()
        self.notificationCallback = NotificationCallback(self)
        self.deviceEnumerator.RegisterEndpointNotificationCallback(
            self.notificationCallback
        )

    def initialize(self):
        self.masterVolume = self.audioManager.getMasterVolume()

    def terminate(self):
        super().terminate()
        self.deviceEnumerator.UnregisterEndpointNotificationCallback(
            self.notificationCallback
        )

    def event_UIA_notification(self, obj, next, **kwargs):
        if (
            obj.appModule.appName == "explorer"
            and "activityId" in kwargs
            and kwargs["activityId"] == "Windows.Shell.VolumeAnnouncement"
        ):
            return
        next()

    @doc(_("Decrease volume"))
    def script_decreaseVolume(self, gesture):
        self.changeVolume(-1)

    @doc(_("Increase volume"))
    def script_increaseVolume(self, gesture):
        self.changeVolume(1)

    def changeVolume(self, amount):
        """amount - relative percentage."""
        oldVolume = self.currentApp.volume
        newVolume = oldVolume + amount
        newVolume = max(0, min(100, newVolume))
        if oldVolume == newVolume:
            tones.beep(200 if amount < 0 else 500, 100)
            return
        self.currentApp.volume = newVolume
        ui.message(f"{newVolume}%")

    def script_onVolumeDown(self, gesture):
        self.masterVolume.session.VolumeStepDown(None)
        self.onSystemVolumeChange()

    def script_onVolumeUp(self, gesture):
        self.masterVolume.session.VolumeStepUp(None)
        self.onSystemVolumeChange()

    def onSystemVolumeChange(self):
        # NVDA ignores multimedia keys and does not stop speech.
        cancelSpeech()
        ui.message(f"{self.masterVolume.volume}%")

    @doc(_("Previous app"))
    def script_moveToPreviousApp(self, gesture):
        self.changeApp(-1)

    @doc(_("Next app"))
    def script_moveToNextApp(self, gesture):
        self.changeApp(1)

    def changeApp(self, offset):
        self.currentAppIndex = (self.currentAppIndex + offset) % len(self.apps)
        self.currentApp = self.apps[self.currentAppIndex]
        ui.message(f"{self.currentApp.name} {self.currentApp.volume}%")

    def script_setVolume(self, gesture):
        self.clearGestureBindings()
        currentValue = self.currentApp.volume
        gui.mainFrame._popupSettingsDialog(ChangeVolumeDialog, self, value=currentValue)

    def setVolume(self, volume):
        self.currentApp.volume = volume
        self.setOverlayGestures()

    def script_muteApp(self, gesture):
        self.currentApp.muted = not self.currentApp.muted
        ui.message(_("muted") if self.currentApp.muted else _("unmuted"))

    def script_toggleOverlay(self, gesture):
        self.overlayActive = not self.overlayActive
        if not self.overlayActive:
            tones.beep(440, 100)
            self.setBaseGestures()
            return
        self.apps = [self.masterVolume]
        self.currentAppIndex = 0
        for session in self.audioManager.getAllSessions():
            self.apps.append(session)
            if session.name == self.currentApp.name:
                self.currentAppIndex = len(self.apps) - 1
        self.currentApp = self.apps[self.currentAppIndex]
        tones.beep(660, 100)
        self.setOverlayGestures()

    def setBaseGestures(self):
        self.clearGestureBindings()
        self.bindGestures(self.baseGestures)

    def setOverlayGestures(self):
        self.clearGestureBindings()
        self.bindGestures(self.baseGestures)
        self.bindGestures(self.overlayGestures)
