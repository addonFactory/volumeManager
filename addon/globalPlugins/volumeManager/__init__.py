# VolumeManager NVDA addon
# Authors: Danstiv, Beqa gozalishvili
# Copyright 2019-2024, released under GPL.

import addonHandler
import globalPluginHandler
import tones
import ui
from pycaw.utils import AudioUtilities
from scriptHandler import getLastScriptRepeatCount
from speech import cancelSpeech

from .audioManager import AudioManager, DefaultDevice, DeviceSession
from .constants import BASE_GESTURES, OVERLAY_GESTURES, VOLUME_CHANGE_AMOUNT_MAP
from .enums import DeviceType
from .notification_callback import NotificationCallback

addonHandler.initTranslation()

FEATURE_NOT_SUPPORTED_TEXT = _("Action is not supported")


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "Volume Manager"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audioManager = AudioManager()
        self.fetchDevices()
        self.sessions = [self.outputDeviceSession]
        self.currentSession = None
        self.currentSessionIndex = 0
        self.currentSessionDevices = []
        self.currentSessionDeviceIndex = 0
        self.deviceType = DeviceType.OUTPUT
        self.switchSession(0)
        self.overlayActive = False
        self.setBaseGestures()
        self.deviceEnumerator = AudioUtilities.GetDeviceEnumerator()
        self.notificationCallback = NotificationCallback(self)
        self.deviceEnumerator.RegisterEndpointNotificationCallback(
            self.notificationCallback
        )

    @staticmethod
    def getDeviceName(device):
        if device is DefaultDevice:
            return _("Default device")
        if device is None:
            return
        return device.name

    def fetchDevices(self):
        self.inputDevice = self.audioManager.getDefaultInputDevice()
        self.outputDevice = self.audioManager.getDefaultOutputDevice()
        self.inputDevices = self.audioManager.getInputDevices()
        self.outputDevices = self.audioManager.getOutputDevices()
        self.outputDeviceSession = DeviceSession(
            _("Output device"), self.outputDevice, DeviceType.OUTPUT
        )
        self.inputDeviceSession = DeviceSession(
            _("Input device"), self.inputDevice, DeviceType.INPUT
        )

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

    def script_changeVolume(self, gesture):
        amount = VOLUME_CHANGE_AMOUNT_MAP[gesture.mainKeyName]
        self.changeVolume(amount)

    def script_setVolume(self, gesture):
        amount = int(gesture.mainKeyName) * 10
        # We want max volume when the 0 key is pressed
        amount = 100 if amount == 0 else amount
        self.changeVolume(amount, False)

    def changeVolume(self, amount, relative=True):
        oldVolume = self.currentSession.volume
        newVolume = oldVolume + amount if relative else amount
        newVolume = max(0, min(100, newVolume))
        if oldVolume == newVolume:
            tones.beep(200 if amount < 0 else 500, 100)
            return
        self.currentSession.volume = newVolume
        ui.message(f"{newVolume}%")

    def script_onVolumeDown(self, gesture):
        self.outputDeviceSession.session.VolumeStepDown(None)
        self.onSystemVolumeChange()

    def script_onVolumeUp(self, gesture):
        self.outputDeviceSession.session.VolumeStepUp(None)
        self.onSystemVolumeChange()

    def onSystemVolumeChange(self):
        # NVDA ignores multimedia keys and does not stop speech.
        cancelSpeech()
        ui.message(f"{self.outputDeviceSession.volume}%")

    def script_switchSession(self, gesture):
        offset = -1 if gesture.mainKeyName == "leftArrow" else 1
        newSessionIndex = (self.currentSessionIndex + offset) % len(self.sessions)
        self.switchSession(newSessionIndex)
        if isinstance(self.currentSession, DeviceSession):
            device = self.currentSession.device
        else:
            device = (
                self.currentSession.inputDevice
                if self.deviceType == DeviceType.INPUT
                else self.currentSession.outputDevice
            )
        deviceName = self.getDeviceName(device)
        message = f"{self.currentSession.name} {self.currentSession.volume}%"
        if deviceName is not None:
            message += f" - {deviceName}"
        ui.message(message)

    def switchSession(self, sessionIndex):
        self.currentSessionIndex = sessionIndex
        self.currentSession = self.sessions[self.currentSessionIndex]
        self.currentSessionDevices = []
        self.currentSessionDeviceIndex = 0
        if isinstance(self.currentSession, DeviceSession):
            deviceType = self.currentSession.deviceType
            currentSessionDevice = self.currentSession.device
        else:
            deviceType = self.deviceType
            currentSessionDevice = (
                self.currentSession.inputDevice
                if deviceType == DeviceType.INPUT
                else self.currentSession.outputDevice
            )
            self.currentSessionDevices = [DefaultDevice]
        self.currentSessionDevices.extend(
            self.inputDevices if deviceType == DeviceType.INPUT else self.outputDevices
        )
        for i, device in enumerate(self.currentSessionDevices):
            if device == currentSessionDevice:
                self.currentSessionDeviceIndex = i
                break

    def setVolume(self, volume):
        self.currentSession.volume = volume
        self.setOverlayGestures()

    def script_muteSession(self, gesture):
        self.currentSession.muted = not self.currentSession.muted
        ui.message(_("muted") if self.currentSession.muted else _("unmuted"))

    def script_cycleDeviceTypes(self, gesture):
        value = (self.deviceType.value + 1) % len(DeviceType)
        self.deviceType = DeviceType(value)
        self.switchSession(self.currentSessionIndex)
        ui.message(
            _("Input devices")
            if self.deviceType == DeviceType.INPUT
            else _("Output devices")
        )

    def script_switchDevice(self, gesture):
        if (
            not isinstance(self.currentSession, DeviceSession)
            and not AudioManager.sessionDeviceSettingsIsSupported
        ):
            ui.message(FEATURE_NOT_SUPPORTED_TEXT)
            return
        offset = -1 if gesture.mainKeyName == "upArrow" else 1
        oldIndex = self.currentSessionDeviceIndex
        newIndex = max(0, min(len(self.currentSessionDevices) - 1, oldIndex + offset))
        self.currentSessionDeviceIndex = newIndex
        device = self.currentSessionDevices[self.currentSessionDeviceIndex]
        ui.message(self.getDeviceName(device))
        if oldIndex == newIndex:
            tones.beep(200 if offset < 0 else 500, 50)

    def script_setDevice(self, gesture):
        if (
            not isinstance(self.currentSession, DeviceSession)
            and not AudioManager.sessionDeviceSettingsIsSupported
        ):
            ui.message(FEATURE_NOT_SUPPORTED_TEXT)
            return
        newDevice = self.currentSessionDevices[self.currentSessionDeviceIndex]
        if isinstance(self.currentSession, DeviceSession):
            deviceAttributeName = "device"
        else:
            deviceAttributeName = (
                "inputDevice" if self.deviceType == DeviceType.INPUT else "outputDevice"
            )
        currentDevice = getattr(self.currentSession, deviceAttributeName)
        if currentDevice is None:
            # Sometimes we get such strange sessions,
            # for example@%SystemRoot%\System32\AudioSrv.Dll,-202
            # Getting the default device for such sessions causes an exception,
            # trying to set another device also results in an exception.
            ui.message(_("Operation not supported"))
            return
        if currentDevice == newDevice:
            tones.beep(350, 100)
            return
        setattr(self.currentSession, deviceAttributeName, newDevice)
        ui.message(_("Applied"))

    def script_resetConfiguration(self, gesture):
        if (
            not isinstance(self.currentSession, DeviceSession)
            and not AudioManager.sessionDeviceSettingsIsSupported
        ):
            ui.message(FEATURE_NOT_SUPPORTED_TEXT)
            return
        if getLastScriptRepeatCount() < 2:
            ui.message(_("Press three times to reset device configuration"))
            return
        self.audioManager.resetConfiguration()
        ui.message(_("Device configuration reset"))

    def script_toggleOverlay(self, gesture):
        self.overlayActive = not self.overlayActive
        if not self.overlayActive:
            tones.beep(440, 100)
            self.setBaseGestures()
            return
        self.sessions = []
        newSessionIndex = 0
        for session in [
            self.outputDeviceSession,
            self.inputDeviceSession,
            *self.audioManager.getAllSessions(),
        ]:
            self.sessions.append(session)
            if session.name == self.currentSession.name:
                newSessionIndex = len(self.sessions) - 1
        self.switchSession(newSessionIndex)
        tones.beep(660, 100)
        self.setOverlayGestures()

    script_toggleOverlay.__doc__ = _("Toggle Volume Manager virtual screen")

    def setBaseGestures(self):
        self.clearGestureBindings()
        self.bindGestures(BASE_GESTURES)

    def setOverlayGestures(self):
        self.clearGestureBindings()
        self.bindGestures(BASE_GESTURES)
        self.bindGestures(OVERLAY_GESTURES)
