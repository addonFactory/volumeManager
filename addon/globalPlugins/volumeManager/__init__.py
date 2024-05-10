# -*- coding: utf-8 -*-

# VolumeManager NVDA addon
# Authors: Danstiv, Beqa gozalishvili
# Copyright 2019-2023, released under GPL.


import addonHandler
from comtypes import CLSCTX_ALL
from ctypes import POINTER, cast
import globalPluginHandler
import gui
import os
from speech import cancelSpeech
import sys
import tones
import ui

import pycaw
from pycaw.api.endpointvolume import IAudioEndpointVolume
from pycaw.callbacks import MMNotificationClient
from pycaw.utils import AudioUtilities

from .interface import ChangeVolumeDialog

addonHandler.initTranslation()

class NotificationCallback(MMNotificationClient):

    def __init__(self, pluginInstance):
        self.pluginInstance = pluginInstance

    def on_device_state_changed(self, device_id, new_state, new_state_id):
        if new_state_id != 8: return
        self.pluginInstance.initialize()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled = False
        self.app_index = 0
        self.initialize()
        self.current_app = self.master_volume
        self.standard_gestures = {"kb:nvda+shift+v": "turn", "kb:volumeDown": "volume_changed", "kb:volumeUp": "volume_changed"}
        self.gestures = {"kb:leftArrow": "move_to_app", "kb:rightArrow": "move_to_app", "kb:upArrow": "change_volume", "kb:downArrow": "change_volume", "kb:space": "set_volume", "kb:m": "mute_app"}
        self.set_standard_gestures()
        self.deviceEnumerator = AudioUtilities.GetDeviceEnumerator()
        self.notificationCallback = NotificationCallback(self)
        self.deviceEnumerator.RegisterEndpointNotificationCallback(self.notificationCallback)

    def terminate(self):
        super().terminate()
        self.deviceEnumerator.UnregisterEndpointNotificationCallback(self.notificationCallback)

    def initialize(self):
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.master_volume = cast(interface, POINTER(IAudioEndpointVolume))
        self.master_volume.SetMasterVolume = self.master_volume.SetMasterVolumeLevelScalar
        self.master_volume.GetMasterVolume = self.master_volume.GetMasterVolumeLevelScalar
        self.master_volume.name = _("Master volume")

    def event_UIA_notification(self, obj, next, **kwargs):
        if obj.appModule.appName == 'explorer' and "activityId" in kwargs and kwargs["activityId"] == "Windows.Shell.VolumeAnnouncement":
            return
        next()

    def script_change_volume(self, gesture):
        direction = 1 if gesture._get_identifiers()[1].split(":")[-1] == "upArrow" else - 1
        volume = round(self.current_app.GetMasterVolume(), 2)
        if direction == 1:
            if volume >= 1.0:
                tones.beep(500, 100)
                return
            volume += 0.01
        else:
            if volume <= 0.0:
                tones.beep(200, 100)
                return
            volume -= 0.01
        self.current_app.SetMasterVolume(volume, None)
        ui.message(str(int(round(volume * 100, 0))) + "%")

    def script_volume_changed(self, gesture):
        gesture.send()
        cancelSpeech()
        ui.message(str(int(round(round(self.master_volume.GetMasterVolume(), 2) * 100, 0))) + "%")

    def script_move_to_app(self, gesture):
        direction = 1 if gesture._get_identifiers()[1].split(":")[-1] == "rightArrow" else - 1
        l = len(self.apps)
        i = self.app_index
        i = i + 1 if direction == 1 else i - 1
        if i < 0:
            i = l - 1
        if i >= l:
            i = 0
        self.app_index = i
        self.current_app = self.apps[self.app_index]
        ui.message(self.current_app.name + " " + str(int(round(round(self.current_app.GetMasterVolume(), 2) * 100, 0))) + " %")

    def script_set_volume(self, gesture):
        self.clearGestureBindings()
        currentValue = int(round(round(self.current_app.GetMasterVolume(), 2) * 100, 0))
        gui.mainFrame._popupSettingsDialog(ChangeVolumeDialog, self, value=currentValue)

    def set_volume(self, volume):
        self.current_app.SetMasterVolume(volume / 100.0, None)
        self.set_all_gestures()

    def script_mute_app(self, gesture):
        muteState = self.current_app.GetMute()
        if muteState == 0:
            self.current_app.SetMute(1, None)
            ui.message(_("muted"))
        elif muteState == 1:
            self.current_app.SetMute(0, None)
            ui.message(_("unmuted"))

    def script_turn(self, gesture):
        self.enabled = not self.enabled
        if not self.enabled:
            tones.beep(440, 100)
            self.set_standard_gestures()
            return
        all_sessions = AudioUtilities.GetAllSessions()
        self.apps = []
        del self.app_index
        self.apps.append(self.master_volume)
        for session in all_sessions:
            if session.Process:
                s = session.SimpleAudioVolume
                s.name = session.DisplayName or session.Process.name()
                self.apps.append(s)
                if s.name == self.current_app.name:
                    self.app_index = len(self.apps) - 1
        if not hasattr(self, "app_index"):
            self.app_index = 0
        self.current_app = self.apps[self.app_index]
        tones.beep(660, 100)
        self.set_all_gestures()

    def set_standard_gestures(self):
        self.clearGestureBindings()
        self.bindGestures(self.standard_gestures)

    def set_all_gestures(self):
        self.clearGestureBindings()
        self.bindGestures(self.standard_gestures)
        self.bindGestures(self.gestures)
