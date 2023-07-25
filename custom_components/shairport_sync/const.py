"""Provides the constants needed for this component."""
from homeassistant.backports.enum import StrEnum

DOMAIN = "shairport_sync"

# OFF_STATES = [STATE_IDLE, STATE_OFF, STATE_UNAVAILABLE]


class Command(StrEnum):
    """Remote commands for Shairport Sync."""

    PAUSE = "pause"
    PLAY = "play"
    STOP = "stop"
    SKIP_NEXT = "nextitem"
    SKIP_PREVIOUS = "previtem"
    VOLUME_DOWN = "volumedown"
    VOLUME_UP = "volumeup"
    VOLUME_MUTE = "mutetoggle"


class TopLevelTopic(StrEnum):
    """Top level topics for Shairport Sync."""

    ARTIST = "artist"
    ALBUM = "album"
    COVER = "cover"
    PLAY_END = "play_end"
    PLAY_FLUSH = "play_flush"
    PLAY_START = "play_start"
    PLAY_RESUME = "play_resume"
    ACTIVE_END = "active_end"
    REMOTE = "remote"
    TITLE = "title"
