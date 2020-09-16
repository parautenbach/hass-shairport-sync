"""For media players that are controlled via MQTT."""
import logging
import os.path
import uuid

import voluptuous as vol

from homeassistant.components.media_player import (
    DEVICE_CLASS_SPEAKER,
    PLATFORM_SCHEMA,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_STOP,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.components.mqtt import ATTR_TOPIC, async_publish, async_subscribe
from homeassistant.components.mqtt.util import (
    valid_publish_topic,
    valid_subscribe_topic,
)
from homeassistant.const import CONF_NAME, STATE_IDLE, STATE_PAUSED, STATE_PLAYING
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.network import get_url

from .const import (
    COMMAND_PAUSE,
    COMMAND_PLAY,
    COMMAND_SKIP_NEXT,
    COMMAND_SKIP_PREVIOUS,
    COMMAND_VOLUME_DOWN,
    COMMAND_VOLUME_UP,
    CONF_METADATA,
    CONF_REMOTE,
    CONF_STATES,
    METADATA_ARTIST,
    METADATA_ARTWORK,
    METADATA_TITLE,
)

_LOGGER = logging.getLogger(__name__)

REMOTE_SCHEMA = vol.All(vol.Schema({vol.Required(ATTR_TOPIC): valid_publish_topic,}),)

STATES_SCHEMA = cv.schema_with_slug_keys(
    vol.All(vol.Schema({vol.Required(ATTR_TOPIC): valid_subscribe_topic,}))
)

METADATA_SCHEMA = cv.schema_with_slug_keys(
    vol.All(vol.Schema({vol.Required(ATTR_TOPIC): valid_subscribe_topic,}))
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_REMOTE): REMOTE_SCHEMA,
        vol.Required(CONF_STATES): STATES_SCHEMA,
        vol.Required(CONF_METADATA): METADATA_SCHEMA,
    },
    extra=vol.REMOVE_EXTRA,
)

SUPPORTED_FEATURES = (
    SUPPORT_PLAY
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_PAUSE
    | SUPPORT_STOP
    | SUPPORT_NEXT_TRACK
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_VOLUME_STEP
)
# flags |= SUPPORT_TURN_ON
# flags |= SUPPORT_TURN_OFF
# flags |= SUPPORT_VOLUME_SET

_PUBLIC_HASS_DIR = "www"
_PUBLIC_HASS_PATH = "local"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the MQTT media players."""
    _LOGGER.debug(config)
    player = ShairportSyncMediaPlayer(
        hass,
        config.get(CONF_NAME),
        config.get(CONF_REMOTE),
        config.get(CONF_STATES),
        config.get(CONF_METADATA),
    )

    async_add_entities([player])


class ShairportSyncMediaPlayer(MediaPlayerEntity):
    """Representation of an MQTT-controlled media player."""

    def __init__(self, hass, name, remote, states, metadata):
        """Initialize the MQTT media device."""
        _LOGGER.debug("Initialising %s", name)
        self.hass = hass
        self._name = name
        self._remote = remote
        self._states = states
        self._metadata = metadata
        self._player_state = STATE_IDLE
        self._title = None
        self._artist = None
        self._media_image_url = None
        self._subscriptions = []

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        await self._subscribe_to_topics()

    async def async_will_remove_from_hass(self):
        """Run when entity will be removed from hass."""
        _LOGGER.debug("Removing %s subscriptions", len(self._subscriptions))
        for unsubscribe in self._subscriptions:
            await unsubscribe()

    async def _subscribe_to_topics(self):
        """(Re)Subscribe to topics."""

        @callback
        def play_started(_):
            """Handle the play MQTT message."""
            _LOGGER.debug("Play started")
            self._player_state = STATE_PLAYING
            self.async_write_ha_state()

        @callback
        def play_ended(_):
            """Handle the pause MQTT message."""
            _LOGGER.debug("Play ended")
            self._player_state = STATE_PAUSED
            self.async_write_ha_state()

        @callback
        def artist_updated(message):
            """Handle the artist updated MQTT message."""
            self._artist = message.payload
            _LOGGER.debug("New artist: %s", self._artist)
            self.async_write_ha_state()

        @callback
        def title_updated(message):
            """Handle the title updated MQTT message."""
            self._title = message.payload
            _LOGGER.debug("New title: %s", self._title)
            self.async_write_ha_state()

        @callback
        def artwork_updated(message):
            """Handle the artwork updated MQTT message."""
            # https://en.wikipedia.org/wiki/Magic_number_%28programming%29
            # https://en.wikipedia.org/wiki/List_of_file_signatures
            header = " ".join("{:02X}".format(b) for b in message.payload[:4])
            _LOGGER.debug(
                "New artwork (%s bytes); header: %s", len(message.payload), header
            )

            filename = f"{self.entity_id}.{METADATA_ARTWORK}"
            full_path = os.path.join(self.hass.config.path(_PUBLIC_HASS_DIR), filename)
            _LOGGER.debug(full_path)
            with open(full_path, "wb") as image_fd:
                image_fd.write(message.payload)

            # since we're overwriting with the same filename we need to make it
            # look unique in order for the hash to be different
            self._media_image_url = (
                f"{get_url(self.hass)}/{_PUBLIC_HASS_PATH}/{filename}?{uuid.uuid1()}"
            )
            _LOGGER.debug(self._media_image_url)
            self.async_write_ha_state()

        topic = self._states[STATE_PLAYING][ATTR_TOPIC]
        _LOGGER.debug("Subscribing to %s state topic: %s", STATE_PLAYING, topic)
        subscription = await async_subscribe(self.hass, topic, play_started)
        self._subscriptions.append(subscription)

        topic = self._states[STATE_PAUSED][ATTR_TOPIC]
        _LOGGER.debug("Subscribing to %s state topic: %s", STATE_PAUSED, topic)
        subscription = await async_subscribe(self.hass, topic, play_ended)
        self._subscriptions.append(subscription)

        topic = self._metadata[METADATA_ARTIST][ATTR_TOPIC]
        _LOGGER.debug(
            "Subscribing to metadata topic for %s: %s", METADATA_ARTIST, topic
        )
        subscription = await async_subscribe(self.hass, topic, artist_updated)
        self._subscriptions.append(subscription)

        topic = self._metadata[METADATA_TITLE][ATTR_TOPIC]
        _LOGGER.debug("Subscribing to metadata topic for %s: %s", METADATA_TITLE, topic)
        subscription = await async_subscribe(self.hass, topic, title_updated)
        self._subscriptions.append(subscription)

        if os.path.exists(self.hass.config.path(_PUBLIC_HASS_DIR)):
            topic = self._metadata[METADATA_ARTWORK][ATTR_TOPIC]
            _LOGGER.debug(
                "Subscribing to metadata topic for %s: %s", METADATA_ARTWORK, topic
            )
            subscription = await async_subscribe(
                self.hass, topic, artwork_updated, encoding=None
            )
            self._subscriptions.append(subscription)
        else:
            _LOGGER.warning(
                "Artwork won't be saved; no %s directory for public access",
                _PUBLIC_HASS_DIR,
            )

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the player."""
        _LOGGER.debug("Getting name: %s", self._name)
        return self._name

    @property
    def state(self):
        """Return the current state of the media player."""
        _LOGGER.debug("Getting state: %s", self._player_state)
        return self._player_state

    @property
    def media_content_type(self):
        """Return the content type of currently playing media."""
        _LOGGER.debug("Getting media content type: %s", MEDIA_TYPE_MUSIC)
        return MEDIA_TYPE_MUSIC

    @property
    def media_title(self):
        """Title of current playing media."""
        _LOGGER.debug("Getting media title: %s", self._title)
        return self._title

    @property
    def media_artist(self):
        """Artist of current playing media, music track only."""
        _LOGGER.debug("Getting media artist: %s", self._artist)
        return self._artist

    @property
    def media_image_url(self):
        """Image URL of currently playing media."""
        _LOGGER.debug("Getting media image URL: %s", self._media_image_url)
        return self._media_image_url

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORTED_FEATURES

    @property
    def device_class(self):
        return DEVICE_CLASS_SPEAKER

    # is_on
    # async def async_turn_on(self):  # async?
    #     """Turn the media player on."""
    # async def async_turn_off(self):  # async?
    #     """Turn the media player off."""

    async def async_media_play(self):
        """Send play command."""
        _LOGGER.debug("Sending play command")
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PLAY)

    async def async_media_pause(self):
        """Send pause command."""
        _LOGGER.debug("Sending pause command")
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PAUSE)

    async def async_media_stop(self):
        """Send stop command."""
        _LOGGER.debug("Sending stop command")
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PAUSE)

    async def async_media_previous_track(self):
        """Send previous track command."""
        _LOGGER.debug("Sending skip previous command")
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_SKIP_PREVIOUS)

    async def async_media_next_track(self):
        """Send next track command."""
        _LOGGER.debug("Sending skip next command")
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_SKIP_NEXT)

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Play a piece of media."""
        _LOGGER.debug("Sending play media command")
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PLAY)

    async def async_volume_up(self):
        """Turn volume up for media player."""
        _LOGGER.debug("Sending volume up command")
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_VOLUME_UP)

    async def async_volume_down(self):
        """Turn volume down for media player."""
        _LOGGER.debug("Sending volume down command")
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_VOLUME_DOWN)

    async def async_media_play_pause(self):
        """Play or pause the media player."""
        _LOGGER.debug(
            "Sending toggle play/pause command; currently %s", self._player_state
        )
        if self._player_state == STATE_PLAYING:
            async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PAUSE)
        else:
            async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PLAY)


# todo: reload (https://github.com/custom-components/blueprint/blob/master/custom_components/blueprint/__init__.py)
