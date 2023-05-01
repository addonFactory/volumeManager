# -*- coding: utf-8 -*-

# VolumeManager NVDA addon
# Authors: Danstiv, Beqa gozalishvili
# Copyright 2023, released under GPL.

from gui import guiHelper, nvdaControls
import wx


class ChangeVolumeDialog(wx.Dialog):
    def __init__(self, parent=None, pluginInstance=None, value=100):
        super().__init__(parent, title=_("Set volume"))
        self.pluginInstance = pluginInstance
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)
        self.volume_field = sHelper.addLabeledControl(_("Volume"), nvdaControls.SelectOnFocusSpinCtrl, min=0, max=100, initial=value, style=wx.SP_ARROW_KEYS|wx.TE_PROCESS_ENTER)
        self.volume_field.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        buttonGroup = guiHelper.ButtonHelper(wx.VERTICAL)
        ok_btn = buttonGroup.addButton(self, wx.ID_OK, label=_("OK"))
        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        cancel_btn = buttonGroup.addButton(self, wx.ID_CANCEL, label=_("Cancel"))
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        sHelper.addItem(buttonGroup)
        mainSizer.Add(sHelper.sizer, border=10, flag=wx.ALL)
        mainSizer.Fit(self)
        self.SetSizer(mainSizer)
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_enter(self, event):
        self.set()
        self.Close()

    def on_ok(self, event):
        self.set()
        event.Skip()

    def on_cancel(self, event):
        self.pluginInstance.set_all_gestures()
        event.Skip()

    on_close = on_cancel

    def set(self):
        self.pluginInstance.set_volume(self.volume_field.GetValue())
