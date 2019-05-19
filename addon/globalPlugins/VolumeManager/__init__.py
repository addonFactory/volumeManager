# -*- coding: utf-8 -*-

# VolumeManager NVDA addon
# Authors: Danstiv, Beqa gozalishvili
# Copyright 2019, released under GPL.

import addonHandler
from comtypes import CLSCTX_ALL
from ctypes import POINTER, cast
import globalPluginHandler
import gui
from gui.guiHelper import BoxSizerHelper
import os
from speech import cancelSpeech
import sys
import tones
import ui
import wx
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from . import pycaw
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
del sys.path[-1]

addonHandler.initTranslation()

class Change_volume_dialog(wx.Dialog):
	def __init__(self, parent=None, value=100):
		wx.Dialog.__init__(self, parent, title=_('Set volume'))
		self.main_sizer=BoxSizerHelper(self, wx.VERTICAL)
		self.volume_field=self.main_sizer.addLabeledControl(_('Volume'), wx.SpinCtrl, min=0, max=100, initial=value, style=wx.SP_ARROW_KEYS|wx.TE_PROCESS_ENTER)
		self.Bind(wx.EVT_TEXT_ENTER, self.on_enter, self.volume_field)
		self.btn_sizer=BoxSizerHelper(self, wx.HORIZONTAL)
		self.ok_btn=wx.Button(self, wx.ID_OK, label=_('OK'))
		self.btn_sizer.addItem(self.ok_btn)
		self.Bind(wx.EVT_BUTTON, self.on_ok, self.ok_btn)
		self.cancel_btn=wx.Button(self, wx.ID_CANCEL, label=_('Cancel'))
		self.btn_sizer.addItem(self.cancel_btn)
		self.Bind(wx.EVT_BUTTON, self.on_cancel, self.cancel_btn)
		self.main_sizer.addItem(self.btn_sizer)
		self.SetSizer(self.main_sizer.sizer)
		self.Bind(wx.EVT_SHOW, self.on_show)
		self.Bind(wx.EVT_CLOSE, self.on_close)
	def on_show(self, event):
		self.volume_field.SetFocus()
		self.volume_field.SetSelection(0, -1)
		event.Skip()
	def on_enter(self, event):
		self.set()
		self.Close()
	def on_ok(self, event):
		self.set()
		event.Skip()
	def on_cancel(self, event):
		self.set_all_gestures()
		event.Skip()
	def on_close(self, event):
		self.set_all_gestures()
		event.Skip()
	def set(self):
		self.callback(self.volume_field.GetValue())
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self, *args, **kwargs):
		globalPluginHandler.GlobalPlugin.__init__(self, *args, **kwargs)
		self.enabled=False
		self.app_index=0
		devices = AudioUtilities.GetSpeakers()
		interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
		self.master_volume=cast(interface, POINTER(IAudioEndpointVolume))
		self.master_volume.SetMasterVolume=self.master_volume.SetMasterVolumeLevelScalar
		self.master_volume.GetMasterVolume=self.master_volume.GetMasterVolumeLevelScalar
		self.master_volume.name=_('Master volume')
		self.current_app=self.master_volume
		Change_volume_dialog.callback=self.set_volume
		Change_volume_dialog.set_all_gestures=self.set_all_gestures
		self.standard_gestures={'kb:nvda+shift+v': 'turn', 'kb:volumeDown': 'volume_changed', 'kb:volumeUp': 'volume_changed'}
		self.gestures={'kb:leftArrow': 'move_to_app', 'kb:rightArrow': 'move_to_app', 'kb:upArrow': 'change_volume', 'kb:downArrow': 'change_volume', 'kb:space': 'set_volume', 'kb:m': 'mute_app'}
		self.set_standard_gestures()
	def script_change_volume(self, gesture):
		direction=1 if gesture.logIdentifier.split(':')[-1]=='upArrow' else -1
		volume=round(self.current_app.GetMasterVolume(), 2)
		if direction == 1:
			if volume>=1.0:
				tones.beep(500, 50)
				return
			volume+=0.01
			self.current_app.SetMasterVolume(volume, None)
		else:
			if volume<=0.0:
				tones.beep(250, 50)
				return
			volume-=0.01
			self.current_app.SetMasterVolume(volume, None)
		ui.message(str(int(round(volume*100, 0)))+'%')
	def script_volume_changed(self, gesture):
		gesture.send()
		cancelSpeech()
		ui.message(str(int(round(round(self.master_volume.GetMasterVolume(), 2)*100, 0)))+'%')
	def script_move_to_app(self, gesture):
		direction=1 if gesture.logIdentifier.split(':')[-1]=='rightArrow' else -1
		l=len(self.apps)
		i=self.app_index
		i=i+1 if direction==1 else i-1
		if i<0:
			i=l-1
		if i>=l:
			i=0
		self.app_index=i
		self.current_app=self.apps[self.app_index]
		ui.message(self.current_app.name + ' ' + str(int(round(round(self.current_app.GetMasterVolume(), 2)*100, 0))) + ' %')
	def script_set_volume(self, gesture):
		self.clearGestureBindings()
		gui.mainFrame._popupSettingsDialog(Change_volume_dialog, int(round(round(self.current_app.GetMasterVolume(), 2)*100, 0)))
	def set_volume(self, volume):
		self.current_app.SetMasterVolume(volume/100.0, None)
		self.set_all_gestures()
	def script_mute_app(self, gesture):
		muteState = self.current_app.GetMute()
		if muteState == 0:
			self.current_app.SetMute(1, None)
			ui.message(_('muted'))
		elif muteState == 1:
			self.current_app.SetMute(0, None)
			ui.message(_('unmuted'))
	def script_turn(self, gesture):
		self.enabled=not self.enabled
		if not self.enabled:
			tones.beep(440, 100)
			self.set_standard_gestures()
			return
		all_sessions=AudioUtilities.GetAllSessions()
		self.apps=[]
		del self.app_index
		self.apps.append(self.master_volume)
		for session in all_sessions:
			if session.Process:
				s=session.SimpleAudioVolume
				s.name=session.Process.name()
				self.apps.append(s)
				if s.name==self.current_app.name:
					self.app_index=len(self.apps)-1
		if not hasattr(self, 'app_index'):
			self.app_index=0
		self.current_app=self.apps[self.app_index]
		tones.beep(660, 100)
		self.set_all_gestures()
	def set_standard_gestures(self):
		self.clearGestureBindings()
		self.bindGestures(self.standard_gestures)
	def set_all_gestures(self):
		self.clearGestureBindings()
		self.bindGestures(self.standard_gestures)
		self.bindGestures(self.gestures)
