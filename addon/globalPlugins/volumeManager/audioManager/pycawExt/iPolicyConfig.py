from ctypes import HRESULT, c_int32
from ctypes.wintypes import LPCWSTR

from comtypes import CLSCTX_INPROC_SERVER, COMMETHOD, GUID, CoCreateInstance, IUnknown

from .enums import ERole

CLSID = GUID("{870AF99C-171D-4F9E-AF0D-E63DF40C2BC9}")

INT32 = c_int32


class IPolicyConfig(IUnknown):
    _iid_ = GUID("{F8679F50-850A-41CF-9C72-430F290290C8}")
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
        COMMETHOD(
            [],
            HRESULT,
            "SetDefaultEndpoint",
            (["in"], LPCWSTR, "pwstrDeviceId"),
            (["in"], ERole, "ERole"),
        ),
        COMMETHOD([], INT32, "m12"),
    )


def getPolicyConfig():
    return CoCreateInstance(CLSID, IPolicyConfig, CLSCTX_INPROC_SERVER)
