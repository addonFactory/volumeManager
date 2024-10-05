from ctypes.wintypes import INT

ENUM = INT


class TrustLevel(ENUM):
    BaseTrust = 0
    PartialTrust = BaseTrust + 1
    FullTrust = PartialTrust + 1


class EDataFlow(ENUM):
    eRender = 0
    eCapture = 1
    eAll = 2
    EDataFlow_enum_count = 3


class ERole(ENUM):
    eConsole = 0
    eMultimedia = 1
    eCommunications = 2
    ERole_enum_count = 3
