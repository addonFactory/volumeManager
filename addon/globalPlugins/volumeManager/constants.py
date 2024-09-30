BASE_GESTURES = {
    "kb:nvda+shift+v": "toggleOverlay",
    "kb:volumeDown": "onVolumeDown",
    "kb:volumeUp": "onVolumeUp",
}

OVERLAY_GESTURES = {
    "kb:leftArrow": "switchToApp",
    "kb:rightArrow": "switchToApp",
    "kb:space": "openSetVolumeDialog",
    "kb:m": "muteApp",
}

VOLUME_CHANGE_AMOUNT_MAP = {}

for key, amount in (("downArrow", -1), ("upArrow", 1)):
    OVERLAY_GESTURES[f"kb:{key}"] = "changeVolume"
    VOLUME_CHANGE_AMOUNT_MAP[key] = amount
