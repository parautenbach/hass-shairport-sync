"""Provides the constants needed for this component."""

from homeassistant.components.mqtt import ATTR_TOPIC

# OFF_STATES = [STATE_IDLE, STATE_OFF, STATE_UNAVAILABLE]

COMMAND_PAUSE = "pause"
COMMAND_PLAY = "play"
COMMAND_SKIP_NEXT = "nextitem"
COMMAND_SKIP_PREVIOUS = "previtem"
COMMAND_VOLUME_DOWN = "volumedown"
COMMAND_VOLUME_UP = "volumeup"

CONF_TOPIC = ATTR_TOPIC

TOP_LEVEL_TOPIC_ARTIST = "artist"
TOP_LEVEL_TOPIC_COVER = "cover"
TOP_LEVEL_TOPIC_PLAY_END = "play_end"
TOP_LEVEL_TOPIC_PLAY_START = "play_start"
TOP_LEVEL_TOPIC_REMOTE = "remote"
TOP_LEVEL_TOPIC_TITLE = "title"
