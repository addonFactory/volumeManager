import addonHandler
from comtypes import CLSCTX_ALL
from pycaw.api.endpointvolume import IAudioEndpointVolume
from pycaw.utils import AudioUtilities

addonHandler.initTranslation()


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


class MasterVolumeSession(AudioSession):
    name = _("Master volume")

    def __init__(self, session):
        self.session = session

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


class AudioManager:
    def getMasterVolume(self):
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        masterVolume = interface.QueryInterface(IAudioEndpointVolume)
        return MasterVolumeSession(masterVolume)

    def getAllSessions(self):
        sessions = []
        for session in AudioUtilities.GetAllSessions():
            if not session.Process:
                continue
            sessions.append(AudioSession(session))
        return sessions
