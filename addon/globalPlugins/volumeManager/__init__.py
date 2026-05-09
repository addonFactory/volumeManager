# VolumeManager NVDA addon
# Authors: Danstiv, Beqa gozalishvili
# Copyright 2019-2024, released under GPL.

import addonHandler
import globalPluginHandler
import tones
import ui
from scriptHandler import getLastScriptRepeatCount
from speech import cancelSpeech

from .audioManager import AudioManager, DefaultDevice, DeviceSession
from .constants import BASE_GESTURES, OVERLAY_GESTURES, VOLUME_CHANGE_AMOUNT_MAP
from .enums import DeviceType

addonHandler.initTranslation()

FEATURE_NOT_SUPPORTED_TEXT = _("Action is not supported")


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "Volume Manager"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audioManager = AudioManager()
        self.sessions = []
        self.currentSession = None
        self.currentSessionIndex = 0
        self.currentSessionDevices = []
        self.currentSessionDeviceIndex = 0
        self.controllingDeviceType = DeviceType.OUTPUT
        self.overlayActive = False
        self.setBaseGestures()

    @property
    def _sessionDeviceSwitchingSupported(self):
        return (
            isinstance(self.currentSession, DeviceSession)
            or AudioManager.sessionDeviceSettingsIsSupported
        )

    @staticmethod
    def getDeviceName(device):
        if device is DefaultDevice:
            return _("Default device")
        return device.name

    def getSessionName(self, session):
        if not isinstance(session, DeviceSession) and session.isSystemSounds:
            return _("System sounds")
        return session.name

    def terminate(self):
        super().terminate()
        self.audioManager.terminate()

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
        self.audioManager.defaultOutputDevice.EndpointVolume.VolumeStepDown(None)
        self.onSystemVolumeChange()

    def script_onVolumeUp(self, gesture):
        self.audioManager.defaultOutputDevice.EndpointVolume.VolumeStepUp(None)
        self.onSystemVolumeChange()

    def onSystemVolumeChange(self):
        # NVDA ignores multimedia keys and does not stop speech.
        cancelSpeech()
        ui.message(f"{self.audioManager.defaultOutputDevice.volume}%")

    def script_switchSession(self, gesture):
        offset = -1 if gesture.mainKeyName == "leftArrow" else 1
        newSessionIndex = (self.currentSessionIndex + offset) % len(self.sessions)
        self.switchSession(newSessionIndex)
        if isinstance(self.currentSession, DeviceSession):
            device = self.currentSession.device
        else:
            device = (
                self.currentSession.inputDevice
                if self.controllingDeviceType == DeviceType.INPUT
                else self.currentSession.outputDevice
            )
        message = (
            f"{self.getSessionName(self.currentSession)} {self.currentSession.volume}%"
        )
        if device is not None:
            message += f" - {self.getDeviceName(device)}"
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
            deviceType = self.controllingDeviceType
            currentSessionDevice = (
                self.currentSession.inputDevice
                if deviceType == DeviceType.INPUT
                else self.currentSession.outputDevice
            )
            self.currentSessionDevices = [DefaultDevice]
        self.currentSessionDevices.extend(
            self.audioManager.inputDevices
            if deviceType == DeviceType.INPUT
            else self.audioManager.outputDevices
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
        value = (self.controllingDeviceType.value + 1) % len(DeviceType)
        self.controllingDeviceType = DeviceType(value)
        self.switchSession(self.currentSessionIndex)
        ui.message(
            _("Input devices")
            if self.controllingDeviceType == DeviceType.INPUT
            else _("Output devices")
        )

    def script_switchDevice(self, gesture):
        if not self._sessionDeviceSwitchingSupported:
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
        if not self._sessionDeviceSwitchingSupported:
            ui.message(FEATURE_NOT_SUPPORTED_TEXT)
            return
        if isinstance(self.currentSession, DeviceSession):
            deviceAttributeName = "device"
        else:
            if self.currentSession.isSystemSounds:
                ui.message(_("Operation not supported"))
                return
            deviceAttributeName = (
                "inputDevice"
                if self.controllingDeviceType == DeviceType.INPUT
                else "outputDevice"
            )
        currentDevice = getattr(self.currentSession, deviceAttributeName)
        newDevice = self.currentSessionDevices[self.currentSessionDeviceIndex]
        if currentDevice == newDevice:
            tones.beep(350, 100)
            return
        setattr(self.currentSession, deviceAttributeName, newDevice)
        ui.message(_("Applied"))

    def script_resetConfiguration(self, gesture):
        if not self._sessionDeviceSwitchingSupported:
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
        defaultInputDevice = self.audioManager.defaultInputDevice
        defaultOutputDevice = self.audioManager.defaultOutputDevice
        _sessions = []
        if defaultOutputDevice is not None:
            _sessions.append(
                DeviceSession(
                    _("Output device"), defaultOutputDevice, DeviceType.OUTPUT
                )
            )
        if defaultInputDevice is not None:
            _sessions.append(
                DeviceSession(_("Input device"), defaultInputDevice, DeviceType.INPUT)
            )
        _sessions.extend(self.audioManager.getAllSessions())
        self.sessions = []
        newSessionIndex = 0
        for session in _sessions:
            self.sessions.append(session)
            if (
                self.currentSession is not None
                and session.name == self.currentSession.name
            ):
                newSessionIndex = len(self.sessions) - 1
        self.switchSession(newSessionIndex)
        tones.beep(660, 100)
        self.setOverlayGestures()

    script_toggleOverlay.__doc__ = _("Toggle Volume Manager virtual screen")

    def getScript(self, gesture):
        script = super().getScript(gesture)
        if self.overlayActive is True and script is None:
            return self.script_placeholder
        return script

    def script_placeholder(self, gesture):
        tones.beep(200, 100)

    def setBaseGestures(self):
        self.clearGestureBindings()
        self.bindGestures(BASE_GESTURES)

    def setOverlayGestures(self):
        self.clearGestureBindings()
        self.bindGestures(BASE_GESTURES)
        self.bindGestures(OVERLAY_GESTURES)
