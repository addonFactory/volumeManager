# VolumeManager NVDA addon
# Authors: Danstiv, Beqa gozalishvili
# Copyright 2023, released under GPL.

import wx
from gui import guiHelper, nvdaControls


class ChangeVolumeDialog(wx.Dialog):
    def __init__(self, parent=None, pluginInstance=None, value=100):
        super().__init__(parent, title=_("Set volume"))
        self.pluginInstance = pluginInstance
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sizerHelper = guiHelper.BoxSizerHelper(self, wx.VERTICAL)
        self.volumeField = sizerHelper.addLabeledControl(
            _("Volume"),
            nvdaControls.SelectOnFocusSpinCtrl,
            min=0,
            max=100,
            initial=value,
            style=wx.SP_ARROW_KEYS | wx.TE_PROCESS_ENTER,
        )
        self.volumeField.Bind(wx.EVT_TEXT_ENTER, self.onEnter)
        buttonGroup = guiHelper.ButtonHelper(wx.VERTICAL)
        okBtn = buttonGroup.addButton(self, wx.ID_OK, label=_("OK"))
        okBtn.Bind(wx.EVT_BUTTON, self.onOk)
        cancelBtn = buttonGroup.addButton(self, wx.ID_CANCEL, label=_("Cancel"))
        cancelBtn.Bind(wx.EVT_BUTTON, self.onCancel)
        sizerHelper.addItem(buttonGroup)
        mainSizer.Add(sizerHelper.sizer, border=10, flag=wx.ALL)
        mainSizer.Fit(self)
        self.SetSizer(mainSizer)
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def onEnter(self, event):
        self.set()
        self.Close()

    def onOk(self, event):
        self.set()
        event.Skip()

    def onCancel(self, event):
        self.pluginInstance.setOverlayGestures()
        event.Skip()

    onClose = onCancel

    def set(self):
        self.pluginInstance.setVolume(self.volumeField.GetValue())
