from ctypes import (
    POINTER,
    c_int32,
    c_int64,
    c_uint,
    c_uint32,
    c_void_p,
    c_wchar_p,
    cast,
    windll,
)
from ctypes.wintypes import HANDLE, ULONG

import winVersion
from comtypes import COMMETHOD, GUID, HRESULT, IUnknown

from .constants import (
    AUDIO_POLICY_CONFIG_VERSION1_BUILD,
    AUDIO_POLICY_CONFIG_VERSION2_BUILD,
)
from .enums import EDataFlow, ERole, TrustLevel

REFIID = POINTER(GUID)

IID = GUID
INT32 = c_int32
INT64 = c_int64


class HSTRING(HANDLE):
    """Required to avoid casting to int by comtypes."""

    pass


PHSTRING = POINTER(HSTRING)
FACTORY = POINTER(c_void_p)

IID_IInspectable = GUID("{AF86E2E0-B12D-4C6A-9C5A-D7AA65101E90}")
winBuild = winVersion.getWinVer().build
if winBuild >= AUDIO_POLICY_CONFIG_VERSION2_BUILD:
    IID_IAudioPolicyConfig = GUID("{ab3d4648-e242-459f-b02f-541c70306324}")
elif winBuild >= AUDIO_POLICY_CONFIG_VERSION1_BUILD:
    IID_IAudioPolicyConfig = GUID("{2a59116d-6c4f-45e0-a74f-707e3fef9258}")
else:
    IID_IAudioPolicyConfig = None  # pylint: disable=c0103

AUDIO_POLICY_CONFIG_CLASS_NAME = "Windows.Media.Internal.AudioPolicyConfig"

combase = windll.combase
combase.WindowsCreateString.argtypes = [c_wchar_p, c_uint32, PHSTRING]
combase.WindowsGetStringRawBuffer.restype = c_wchar_p
combase.WindowsGetStringRawBuffer.argtypes = [HSTRING, POINTER(c_uint32)]
combase.RoGetActivationFactory.argtypes = [HSTRING, REFIID, POINTER(FACTORY)]


class IInspectable(IUnknown):
    _iid_ = IID_IInspectable
    _methods_ = [
        COMMETHOD(
            [],
            HRESULT,
            "GetIids",
            (["out"], POINTER(ULONG), "iidCount"),
            (["out"], POINTER(POINTER(IID)), "iids"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetRuntimeClassName",
            (["out"], PHSTRING, "className"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetTrustLevel",
            (["out"], POINTER(TrustLevel), "trustLevel"),
        ),
    ]


class IAudioPolicyConfig(IInspectable):
    _iid_ = IID_IAudioPolicyConfig
    _methods_ = (
        COMMETHOD([], INT32, "m1"),
        COMMETHOD([], INT32, "m2"),
        COMMETHOD([], INT32, "m3"),
        COMMETHOD([], INT32, "m4"),
        COMMETHOD([], INT32, "m5"),
        COMMETHOD([], INT32, "m6"),
        COMMETHOD([], INT32, "m7"),
        COMMETHOD([], INT32, "m8"),
        COMMETHOD([], INT32, "m9"),
        COMMETHOD([], INT32, "m10"),
        COMMETHOD([], INT32, "m11"),
        COMMETHOD([], INT32, "m12"),
        COMMETHOD([], INT32, "m13"),
        COMMETHOD([], INT32, "m14"),
        COMMETHOD([], INT32, "m15"),
        COMMETHOD([], INT32, "m16"),
        COMMETHOD([], INT32, "m17"),
        COMMETHOD([], INT32, "m18"),
        COMMETHOD([], INT32, "m19"),
        COMMETHOD(
            [],
            HRESULT,
            "SetPersistedDefaultAudioEndpoint",
            (["in"], c_uint, "processId"),
            (["in"], EDataFlow, "flow"),
            (["in"], ERole, "role"),
            (["in"], HSTRING, "deviceId"),
        ),
        COMMETHOD(
            [],
            HRESULT,
            "GetPersistedDefaultAudioEndpoint",
            (["in"], c_uint, "processId"),
            (["in"], EDataFlow, "flow"),
            (["in"], ERole, "role"),
            (["out"], PHSTRING, "deviceId"),
        ),
        COMMETHOD([], HRESULT, "ClearAllPersistedApplicationDefaultEndpoints"),
    )


def stringToHstring(string):
    hstring = HSTRING()
    combase.WindowsCreateString(string, len(string), hstring)
    return hstring


def hstringToString(hstring):
    return combase.WindowsGetStringRawBuffer(hstring, None)


def getAudioPolicyConfig():
    if IID_IAudioPolicyConfig is None:
        return
    factory = FACTORY()
    combase.RoGetActivationFactory(
        stringToHstring(AUDIO_POLICY_CONFIG_CLASS_NAME),
        GUID(IID_IAudioPolicyConfig),
        factory,
    )
    return cast(factory, POINTER(IAudioPolicyConfig))
