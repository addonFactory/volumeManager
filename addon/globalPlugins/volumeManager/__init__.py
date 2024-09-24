# VolumeManager NVDA addon
# Authors: Danstiv, Beqa gozalishvili
# Copyright 2019-2024, released under GPL.


from ctypes import POINTER, cast

import addonHandler
import globalPluginHandler
import gui
import tones
import ui
from comtypes import CLSCTX_ALL
from pycaw.api.endpointvolume import IAudioEndpointVolume
from pycaw.utils import AudioUtilities
from speech import cancelSpeech

from .interface import ChangeVolumeDialog
from .notification_callback import NotificationCallback
from .utils import doc

addonHandler.initTranslation()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlayActive = False
        self.currentAppIndex = 0
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

    def terminate(self):
        super().terminate()
        self.deviceEnumerator.UnregisterEndpointNotificationCallback(
            self.notificationCallback
        )

    def initialize(self):
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.masterVolume = cast(interface, POINTER(IAudioEndpointVolume))
        self.masterVolume.SetMasterVolume = self.masterVolume.SetMasterVolumeLevelScalar
        self.masterVolume.GetMasterVolume = self.masterVolume.GetMasterVolumeLevelScalar
        self.masterVolume.name = _("Master volume")

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
        oldVolume = round(self.currentApp.GetMasterVolume(), 2)
        newVolume = round(oldVolume + amount / 100, 2)
        newVolume = max(0, min(1, newVolume))
        if oldVolume == newVolume:
            tones.beep(200 if amount < 0 else 500, 100)
            return
        self.currentApp.SetMasterVolume(newVolume, None)
        ui.message(str(round(newVolume * 100)) + "%")

    def script_onVolumeDown(self, gesture):
        self.masterVolume.VolumeStepDown(None)
        self.announceCurrentVolume()

    def script_onVolumeUp(self, gesture):
        self.masterVolume.VolumeStepUp(None)
        self.announceCurrentVolume()

    def announceCurrentVolume(self):
        cancelSpeech()
        ui.message(f"{round(self.masterVolume.GetMasterVolume()*100)} %")

    @doc(_("Previous app"))
    def script_moveToPreviousApp(self, gesture):
        self.changeApp(-1)

    @doc(_("Next app"))
    def script_moveToNextApp(self, gesture):
        self.changeApp(1)

    def changeApp(self, offset):
        self.currentAppIndex = (self.currentAppIndex + offset) % len(self.apps)
        self.currentApp = self.apps[self.currentAppIndex]
        ui.message(
            f"{self.currentApp.name} {round(self.currentApp.GetMasterVolume() * 100)}%"
        )

    def script_setVolume(self, gesture):
        self.clearGestureBindings()
        currentValue = round(self.currentApp.GetMasterVolume() * 100)
        gui.mainFrame._popupSettingsDialog(ChangeVolumeDialog, self, value=currentValue)

    def setVolume(self, volume):
        self.currentApp.SetMasterVolume(volume / 100, None)
        self.setOverlayGestures()

    def script_muteApp(self, gesture):
        isMuted = not self.currentApp.GetMute()
        self.currentApp.SetMute(isMuted, None)
        ui.message(_("muted") if isMuted else _("unmuted"))

    def script_toggleOverlay(self, gesture):
        self.overlayActive = not self.overlayActive
        if not self.overlayActive:
            tones.beep(440, 100)
            self.setBaseGestures()
            return
        allSessions = AudioUtilities.GetAllSessions()
        self.apps = []
        self.currentAppIndex = 0
        self.apps.append(self.masterVolume)
        for session in allSessions:
            if session.Process:
                s = session.SimpleAudioVolume
                s.name = session.DisplayName or session.Process.name()
                self.apps.append(s)
                if s.name == self.currentApp.name:
                    self.currentAppIndex = len(self.apps) - 1
        if not hasattr(self, "app_index"):
            self.currentAppIndex = 0
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
