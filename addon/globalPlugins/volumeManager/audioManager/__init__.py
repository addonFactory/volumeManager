import comtypes
import psutil
from comtypes.hresult import S_OK
from pycaw.api.audiopolicy import IAudioSessionControl2, IAudioSessionManager2
from pycaw.utils import AudioDevice, AudioSession, AudioUtilities

from .notificationCallback import NotificationCallback
from .pycawExt.constants import (
    DEVICE_STATE_ACTIVE,
    INTERNAL_ID_AUDIO_CAPTURE_SUFFIX,
    INTERNAL_ID_AUDIO_RENDER_SUFFIX,
    INTERNAL_ID_PREFIX,
)
from .pycawExt.enums import EDataFlow, ERole
from .pycawExt.iAudioPolicyConfig import (
    getAudioPolicyConfig,
    hstringToString,
    stringToHstring,
)
from .pycawExt.iPolicyConfig import getPolicyConfig

DefaultDevice = type("DefaultDevice", (), {})


class AudioDevice(AudioDevice):
    # Audio policy config ids to devices mapping.
    _cachedDevices = {}

    @property
    def name(self):
        return self.FriendlyName

    @property
    def volume(self):
        return round(self.EndpointVolume.GetMasterVolumeLevelScalar() * 100)

    @volume.setter
    def volume(self, volume):
        self.EndpointVolume.SetMasterVolumeLevelScalar(volume / 100, None)

    @property
    def muted(self):
        return self.EndpointVolume.GetMute()

    @muted.setter
    def muted(self, muted):
        self.EndpointVolume.SetMute(muted, None)

    @classmethod
    def createDevice(cls, dev, flow: EDataFlow):
        device = AudioUtilities.CreateDevice(dev)
        device = cls(device.id, device.state, device.properties, device._dev)
        if flow is EDataFlow.eRender:
            internalIdSuffix = INTERNAL_ID_AUDIO_RENDER_SUFFIX
            o = dev.Activate(IAudioSessionManager2._iid_, comtypes.CLSCTX_ALL, None)
            device.manager = o.QueryInterface(IAudioSessionManager2)
        elif flow is EDataFlow.eCapture:
            internalIdSuffix = INTERNAL_ID_AUDIO_CAPTURE_SUFFIX
        else:
            raise ValueError("Unknown flow")
        internalId = f"{INTERNAL_ID_PREFIX}{device.id}{internalIdSuffix}"
        device.internalId = internalId
        cls._cachedDevices[internalId] = device
        return device

    @classmethod
    def getDeviceByAudioPolicyConfigId(cls, deviceId):
        if deviceId.value is None:
            return DefaultDevice
        deviceId = hstringToString(deviceId)
        if device := cls._cachedDevices.get(deviceId, None):
            return device
        raise RuntimeError("Device not found in cache")

    def __eq__(self, other):
        return isinstance(other, AudioDevice) and self.id == other.id


class AudioSession(AudioSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.isSystemSounds = False
        if self._ctl.IsSystemSoundsSession() == S_OK:
            self.isSystemSounds = True
        self.name = self.DisplayName
        if not self.name:
            try:
                self.name = (
                    self.Process.name()
                    if self.Process is not None
                    else "Unknown session"
                )
            except psutil.NoSuchProcess:
                pass

    @property
    def volume(self):
        return round(self.SimpleAudioVolume.GetMasterVolume() * 100)

    @volume.setter
    def volume(self, volume):
        self.SimpleAudioVolume.SetMasterVolume(volume / 100, None)

    @property
    def muted(self):
        return self.SimpleAudioVolume.GetMute()

    @muted.setter
    def muted(self, muted):
        self.SimpleAudioVolume.SetMute(muted, None)

    @property
    def inputDevice(self):
        if AudioManager.audioPolicyConfig is None or self.isSystemSounds:
            return
        deviceId = AudioManager.audioPolicyConfig.GetPersistedDefaultAudioEndpoint(
            self.ProcessId, EDataFlow.eCapture, ERole.eMultimedia
        )
        return AudioDevice.getDeviceByAudioPolicyConfigId(deviceId)

    @inputDevice.setter
    def inputDevice(self, device):
        self._setDevice(device, EDataFlow.eCapture)

    @property
    def outputDevice(self):
        if AudioManager.audioPolicyConfig is None or self.isSystemSounds:
            return
        deviceId = AudioManager.audioPolicyConfig.GetPersistedDefaultAudioEndpoint(
            self.ProcessId, EDataFlow.eRender, ERole.eMultimedia
        )
        return AudioDevice.getDeviceByAudioPolicyConfigId(deviceId)

    @outputDevice.setter
    def outputDevice(self, device):
        self._setDevice(device, EDataFlow.eRender)

    def _setDevice(self, device, flow):
        if device is DefaultDevice:
            device = None
        if AudioManager.audioPolicyConfig is None:
            raise RuntimeError
        deviceId = stringToHstring(device.internalId if device else "")
        for role in [ERole.eConsole, ERole.eCommunications, ERole.eMultimedia]:
            AudioManager.audioPolicyConfig.SetPersistedDefaultAudioEndpoint(
                self.ProcessId, flow, role, deviceId
            )


class DeviceSession(AudioSession):
    def __init__(self, name, device, deviceType):
        self.name = name
        self._device = device
        self.deviceType = deviceType

    @property
    def volume(self):
        return self.device.volume

    @volume.setter
    def volume(self, volume):
        self.device.volume = volume

    @property
    def muted(self):
        return self.device.muted

    @muted.setter
    def muted(self, muted):
        self.device.muted = muted

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, device):
        for role in [ERole.eConsole, ERole.eCommunications, ERole.eMultimedia]:
            AudioManager.policyConfig.SetDefaultEndpoint(device.id, role)
        self._device = device


class AudioManager:
    deviceEnumerator = AudioUtilities.GetDeviceEnumerator()
    audioPolicyConfig = getAudioPolicyConfig()
    policyConfig = getPolicyConfig()
    _deviceCache = {}

    def __init__(self):
        self.inputDevices = []
        self.outputDevices = []
        self.fetchDevices()
        self.notificationCallback = NotificationCallback(self.onDevicesChanged)
        self.deviceEnumerator.RegisterEndpointNotificationCallback(
            self.notificationCallback
        )

    def terminate(self):
        self.deviceEnumerator.UnregisterEndpointNotificationCallback(
            self.notificationCallback
        )

    def onDevicesChanged(self):
        self.fetchDevices()

    @property
    def defaultOutputDevice(self):
        dev = self.deviceEnumerator.GetDefaultAudioEndpoint(
            EDataFlow.eRender, ERole.eMultimedia
        )
        return self._deviceCache[dev.GetId()]

    @property
    def defaultInputDevice(self):
        dev = self.deviceEnumerator.GetDefaultAudioEndpoint(
            EDataFlow.eCapture, ERole.eMultimedia
        )
        return self._deviceCache[dev.GetId()]

    def fetchDevices(self):
        collection = self.deviceEnumerator.EnumAudioEndpoints(
            EDataFlow.eCapture, DEVICE_STATE_ACTIVE
        )
        self.inputDevices = self._getDevicesFromCollection(
            collection, EDataFlow.eCapture
        )
        collection = self.deviceEnumerator.EnumAudioEndpoints(
            EDataFlow.eRender, DEVICE_STATE_ACTIVE
        )
        self.outputDevices = self._getDevicesFromCollection(
            collection, EDataFlow.eRender
        )
        self._deviceCache.clear()
        for device in self.inputDevices + self.outputDevices:
            self._deviceCache[device.id] = device

    def _getDevicesFromCollection(self, collection, flow: EDataFlow):
        devices = []
        count = collection.GetCount()
        for i in range(count):
            device = collection.Item(i)
            if device is not None:
                devices.append(AudioDevice.createDevice(device, flow))
        return devices

    @classmethod
    @property
    def sessionDeviceSettingsIsSupported(cls):
        return cls.audioPolicyConfig is not None

    @classmethod
    def resetConfiguration(cls):
        cls.audioPolicyConfig.ClearAllPersistedApplicationDefaultEndpoints()

    def getAllSessions(self):
        sessions = []
        for device in self.outputDevices:
            ignoreSystemSoundsSession = (
                False if device == self.defaultOutputDevice else True
            )
            sessions.extend(
                self._getDeviceSessions(
                    device.manager, ignoreSystemSoundsSession=ignoreSystemSoundsSession
                )
            )
        return sessions

    @staticmethod
    def _getDeviceSessions(deviceManager, *, ignoreSystemSoundsSession=False):
        sessions = []
        sessionEnumerator = deviceManager.GetSessionEnumerator()
        count = sessionEnumerator.GetCount()
        for i in range(count):
            ctl = sessionEnumerator.GetSession(i)
            ctl2 = ctl.QueryInterface(IAudioSessionControl2)
            session = AudioSession(ctl2)
            if session.isSystemSounds and ignoreSystemSoundsSession:
                continue
            sessions.append(session)
        return sessions
