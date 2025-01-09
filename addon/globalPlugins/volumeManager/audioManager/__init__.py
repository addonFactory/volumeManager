import psutil
from comtypes import CLSCTX_ALL
from pycaw.api.endpointvolume import IAudioEndpointVolume
from pycaw.utils import AudioDevice, AudioUtilities

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

    def __eq__(self, other):
        return isinstance(other, AudioDevice) and self.id == other.id

    @property
    def name(self):
        return self.FriendlyName

    @classmethod
    def createDevice(cls, dev, flow: EDataFlow):
        device = AudioUtilities.CreateDevice(dev)
        device = cls(device.id, device.state, device.properties, device._dev)
        if flow is EDataFlow.eRender:
            internalIdSuffix = INTERNAL_ID_AUDIO_RENDER_SUFFIX
        elif flow is EDataFlow.eCapture:
            internalIdSuffix = INTERNAL_ID_AUDIO_CAPTURE_SUFFIX
        else:
            raise ValueError("Unknown flow")
        internalId = f"{INTERNAL_ID_PREFIX}{device.id}{internalIdSuffix}"
        device.internalId = internalId
        cls._cachedDevices[internalId] = device
        return device


class AudioSession:
    def __init__(self, session):
        self.session = session
        self.name = session.DisplayName or session.Process.name()

    @property
    def volume(self):
        return round(self.session.SimpleAudioVolume.GetMasterVolume() * 100)

    @volume.setter
    def volume(self, volume):
        self.session.SimpleAudioVolume.SetMasterVolume(volume / 100, None)

    @property
    def muted(self):
        return self.session.SimpleAudioVolume.GetMute()

    @muted.setter
    def muted(self, muted):
        self.session.SimpleAudioVolume.SetMute(muted, None)

    @property
    def inputDevice(self):
        if AudioManager.audioPolicyConfig is None:
            return
        deviceId = AudioManager.audioPolicyConfig.GetPersistedDefaultAudioEndpoint(
            self.session.ProcessId, EDataFlow.eCapture, ERole.eMultimedia
        )
        return self._getDeviceById(deviceId)

    @inputDevice.setter
    def inputDevice(self, device):
        self._setDevice(device, EDataFlow.eCapture)

    @property
    def outputDevice(self):
        if AudioManager.audioPolicyConfig is None:
            return
        deviceId = AudioManager.audioPolicyConfig.GetPersistedDefaultAudioEndpoint(
            self.session.ProcessId, EDataFlow.eRender, ERole.eMultimedia
        )
        return self._getDeviceById(deviceId)

    @outputDevice.setter
    def outputDevice(self, device):
        self._setDevice(device, EDataFlow.eRender)

    def _getDeviceById(self, deviceId):
        if deviceId.value is None:
            return DefaultDevice
        deviceId = hstringToString(deviceId)
        if device := AudioDevice._cachedDevices.get(deviceId, None):
            return device
        raise RuntimeError("Device not found in cache")

    def _setDevice(self, device, flow):
        if device is DefaultDevice:
            device = None
        if AudioManager.audioPolicyConfig is None:
            raise RuntimeError
        deviceId = stringToHstring(device.internalId if device else "")
        for role in [ERole.eConsole, ERole.eCommunications, ERole.eMultimedia]:
            AudioManager.audioPolicyConfig.SetPersistedDefaultAudioEndpoint(
                self.session.ProcessId, flow, role, deviceId
            )


class DeviceSession(AudioSession):
    def __init__(self, name, device, deviceType):
        self.name = name
        self._device = device
        self.deviceType = deviceType
        self.initializeSession()

    def initializeSession(self):
        interface = self._device._dev.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None
        )
        self.session = interface.QueryInterface(IAudioEndpointVolume)

    @property
    def volume(self):
        return round(self.session.GetMasterVolumeLevelScalar() * 100)

    @volume.setter
    def volume(self, volume):
        self.session.SetMasterVolumeLevelScalar(volume / 100, None)

    @property
    def muted(self):
        return self.session.GetMute()

    @muted.setter
    def muted(self, muted):
        self.session.SetMute(muted, None)

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, device):
        for role in [ERole.eConsole, ERole.eCommunications, ERole.eMultimedia]:
            AudioManager.policyConfig.SetDefaultEndpoint(device.id, role)
        self._device = device
        self.initializeSession()


class AudioManager:
    deviceEnumerator = AudioUtilities.GetDeviceEnumerator()
    audioPolicyConfig = getAudioPolicyConfig()
    policyConfig = getPolicyConfig()

    @classmethod
    @property
    def sessionDeviceSettingsIsSupported(cls):
        return cls.audioPolicyConfig is not None

    @classmethod
    def resetConfiguration(cls):
        cls.audioPolicyConfig.ClearAllPersistedApplicationDefaultEndpoints()

    def getDefaultInputDevice(self):
        return AudioDevice.createDevice(
            self.deviceEnumerator.GetDefaultAudioEndpoint(
                EDataFlow.eCapture, ERole.eMultimedia
            ),
            EDataFlow.eCapture,
        )

    def getDefaultOutputDevice(self):
        return AudioDevice.createDevice(
            self.deviceEnumerator.GetDefaultAudioEndpoint(
                EDataFlow.eRender, ERole.eMultimedia
            ),
            EDataFlow.eRender,
        )

    def getInputDevices(self):
        collection = self.deviceEnumerator.EnumAudioEndpoints(
            EDataFlow.eCapture, DEVICE_STATE_ACTIVE
        )
        return self._getDevicesFromCollection(collection, EDataFlow.eCapture)

    def getOutputDevices(self):
        collection = self.deviceEnumerator.EnumAudioEndpoints(
            EDataFlow.eRender, DEVICE_STATE_ACTIVE
        )
        return self._getDevicesFromCollection(collection, EDataFlow.eRender)

    def _getDevicesFromCollection(self, collection, flow: EDataFlow):
        devices = []
        count = collection.GetCount()
        for i in range(count):
            device = collection.Item(i)
            if device is not None:
                devices.append(AudioDevice.createDevice(device, flow))
        return devices

    def getAllSessions(self):
        sessions = []
        for session in AudioUtilities.GetAllSessions():
            try:
                sessions.append(AudioSession(session))
            except psutil.NoSuchProcess:
                pass
        return sessions
