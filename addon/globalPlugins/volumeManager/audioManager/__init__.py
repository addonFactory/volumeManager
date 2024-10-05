from comtypes import CLSCTX_ALL
from pycaw.api.endpointvolume import IAudioEndpointVolume
from pycaw.utils import AudioDevice, AudioUtilities

from .pycawExt.constants import AUDIO_POLICY_DEVICE_ID_KEY, DEVICE_STATE_ACTIVE
from .pycawExt.enums import EDataFlow, ERole
from .pycawExt.iAudioPolicyConfig import (
    getAudioPolicyConfig,
    hstringToString,
    stringToHstring,
)
from .pycawExt.iPolicyConfig import getPolicyConfig


class AudioDevice(AudioDevice):
    def __eq__(self, other):
        return isinstance(other, AudioDevice) and self.id == other.id

    @property
    def name(self):
        return self.FriendlyName


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
        deviceId = AudioManager.audioPolicyConfig.GetPersistedDefaultAudioEndpoint(
            self.session.ProcessId, EDataFlow.eCapture, ERole.eMultimedia
        )
        return self._getDeviceById(deviceId)

    @inputDevice.setter
    def inputDevice(self, device):
        self._setDevice(device, EDataFlow.eCapture)

    @property
    def outputDevice(self):
        deviceId = AudioManager.audioPolicyConfig.GetPersistedDefaultAudioEndpoint(
            self.session.ProcessId, EDataFlow.eRender, ERole.eMultimedia
        )
        return self._getDeviceById(deviceId)

    @outputDevice.setter
    def outputDevice(self, device):
        self._setDevice(device, EDataFlow.eRender)

    def _getDeviceById(self, deviceId):
        if deviceId.value is None:
            return
        deviceId = hstringToString(deviceId)
        if device := AudioManager._cachedDevices.get(deviceId, None):
            return device
        raise RuntimeError("Device not found in cache")

    def _setDevice(self, device, flow):
        deviceId = stringToHstring(
            device.properties[AUDIO_POLICY_DEVICE_ID_KEY] if device else ""
        )
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
    # Audio policy config ids to devices mapping.
    _cachedDevices = {}
    audioPolicyConfig = getAudioPolicyConfig()
    policyConfig = getPolicyConfig()

    @classmethod
    def resetConfiguration(cls):
        cls.audioPolicyConfig.ClearAllPersistedApplicationDefaultEndpoints()

    @classmethod
    def createDevice(cls, dev):
        device = AudioUtilities.CreateDevice(dev)
        device = AudioDevice(device.id, device.state, device.properties, device._dev)
        cls._cachedDevices[device.properties[AUDIO_POLICY_DEVICE_ID_KEY]] = device
        return device

    def getDefaultInputDevice(self):
        return self.createDevice(
            self.deviceEnumerator.GetDefaultAudioEndpoint(
                EDataFlow.eCapture, ERole.eMultimedia
            )
        )

    def getDefaultOutputDevice(self):
        return self.createDevice(
            self.deviceEnumerator.GetDefaultAudioEndpoint(
                EDataFlow.eRender, ERole.eMultimedia
            )
        )

    def getInputDevices(self):
        collection = self.deviceEnumerator.EnumAudioEndpoints(
            EDataFlow.eCapture, DEVICE_STATE_ACTIVE
        )
        return self._getDevicesFromCollection(collection)

    def getOutputDevices(self):
        collection = self.deviceEnumerator.EnumAudioEndpoints(
            EDataFlow.eRender, DEVICE_STATE_ACTIVE
        )
        return self._getDevicesFromCollection(collection)

    def _getDevicesFromCollection(self, collection):
        devices = []
        count = collection.GetCount()
        for i in range(count):
            device = collection.Item(i)
            if device is not None:
                devices.append(self.createDevice(device))
        return devices

    def getAllSessions(self):
        sessions = []
        for session in AudioUtilities.GetAllSessions():
            if not session.Process:
                continue
            sessions.append(AudioSession(session))
        return sessions
