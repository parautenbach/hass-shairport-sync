"""For media players that are controlled via MQTT."""
import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    DEVICE_CLASS_SPEAKER,    
    MediaPlayerEntity,
    PLATFORM_SCHEMA, 
)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_STOP,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.components.mqtt import (
    async_subscribe,
    async_publish,
    ATTR_TOPIC,
)
from homeassistant.components.mqtt.util import (
    valid_publish_topic,
    valid_subscribe_topic
)
from homeassistant.const import (
    CONF_NAME,
    STATE_IDLE,
    STATE_PLAYING,
    STATE_PAUSED,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_METADATA,
    CONF_REMOTE,
    CONF_STATES,
    COMMAND_PAUSE,
    COMMAND_PLAY,
    COMMAND_SKIP_NEXT,
    COMMAND_SKIP_PREVIOUS,
    COMMAND_VOLUME_DOWN,
    COMMAND_VOLUME_UP,
    METADATA_ARTIST,
    METADATA_TITLE,
)

_LOGGER = logging.getLogger(__name__)

REMOTE_SCHEMA = vol.All(
                    vol.Schema(
                        {
                            vol.Required(ATTR_TOPIC): valid_publish_topic,
                        }
                    ),
                )

STATES_SCHEMA = cv.schema_with_slug_keys(
    vol.All(
        vol.Schema(
            {
                vol.Required(ATTR_TOPIC): valid_subscribe_topic,
            }
        )
    )
)

METADATA_SCHEMA = cv.schema_with_slug_keys(
    vol.All(
        vol.Schema(
            {
                vol.Required(ATTR_TOPIC): valid_subscribe_topic,
            }
        )
    )
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
    # flags |= SUPPORT_TURN_ON
    # flags |= SUPPORT_TURN_OFF
    SUPPORT_PLAY_MEDIA
    | SUPPORT_PLAY
    | SUPPORT_PAUSE
    | SUPPORT_STOP
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_NEXT_TRACK
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_VOLUME_STEP
    # flags |= SUPPORT_VOLUME_SET
)


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
        _LOGGER.debug("Initialising %s" % name)
        self.hass = hass
        self._name = name
        self._remote = remote
        self._states = states
        self._metadata = metadata
        self._player_state = STATE_IDLE
        # self._subscription_state = None

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        # todo: MediaPlayerEntity? call other supers?
        await super().async_added_to_hass()
        await self._subscribe_to_topics()        
        
    async def async_will_remove_from_hass(self):
        """Run when entity will be removed from hass."""

    async def _subscribe_to_topics(self):
        """(Re)Subscribe to topics."""

        @callback
        def play_started(msg):
            """Handle the play MQTT message."""
            _LOGGER.debug("play_started")
            self._player_state = STATE_PLAYING
            # self.async_write_ha_state()

        @callback
        def play_ended(msg):
            """Handle the pause MQTT message."""
            _LOGGER.debug("play_ended")
            self._player_state = STATE_PAUSED
            # self.async_write_ha_state()

        @callback
        def artist_updated(msg):
            """Handle the artist updated MQTT message."""
            # payload = msg.payload
            _LOGGER.debug("artist_updated")
            # self.async_write_ha_state()

        @callback
        def title_updated(msg):
            """Handle the title updated MQTT message."""
            # payload = msg.payload
            _LOGGER.debug("title_updated")
            # self.async_write_ha_state()

        # todo: capture the remove async state below
        topic = self._states[STATE_PLAYING][ATTR_TOPIC]
        _LOGGER.debug("Subscribing to topic %s (state %s)" % (topic, STATE_PLAYING))
        await async_subscribe(self.hass, topic, play_started)

        topic = self._states[STATE_PAUSED][ATTR_TOPIC]
        _LOGGER.debug("Subscribing to topic %s (state %s)" % (topic, STATE_PAUSED))
        await async_subscribe(self.hass, topic, play_ended)

        topic = self._metadata[METADATA_ARTIST][ATTR_TOPIC]
        _LOGGER.debug("Subscribing to topic %s (metadata %s)" % (topic, METADATA_ARTIST))
        await async_subscribe(self.hass, topic, artist_updated)

        topic = self._metadata[METADATA_TITLE][ATTR_TOPIC]
        _LOGGER.debug("Subscribing to topic %s (metadata %s)" % (topic, METADATA_TITLE))
        await async_subscribe(self.hass, topic, title_updated)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the player."""
        return self._name

    @property
    def state(self):
        """Return the current state of the media player."""
        return self._player_state

    @property
    def media_content_type(self):
        """Return the content type of currently playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        # hass.config.config_path
        # ramanToday at 22:31
        # @Pieter I'm no expert in this, but I believe HA runs in the config folder, 
        # so you would want to store the file at {CURRENT_PATH}/www/{FINAL/PATH/TO/FILE}. 
        # Once you have done that, you can use the get_url function in homeassistant.helpers.network 
        # to get the server BASE URL to create your URL {get_url RETURN}/{FINAL/PATH/TO/FILE}
        # 
        # config_path = hass.config.path(YAML_CONFIG_FILE)
        # hac.allowlist_external_dirs = {hass.config.path("www")}
        return None

    @property
    def entity_picture(self):
        """
        Return image of the media playing.

        The universal media player doesn't use the parent class logic, since
        the url is coming from child entity pictures which have already been
        sent through the API proxy.
        """
        return self.media_image_url

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
    #     await self._async_call_service(SERVICE_TURN_ON, allow_override=True)
    # async def async_turn_off(self):  # async?
    #     """Turn the media player off."""
    #     await self._async_call_service(SERVICE_TURN_OFF, allow_override=True)

    async def async_mute_volume(self, mute):
        """Mute the volume."""
        # data = {ATTR_MEDIA_VOLUME_MUTED: mute}
        # await self._async_call_service(SERVICE_VOLUME_MUTE, data, allow_override=True)

    # async def async_set_volume_level(self, volume):
    #     """Set volume level, range 0..1."""
    #     data = {ATTR_MEDIA_VOLUME_LEVEL: volume}
    #     await self._async_call_service(SERVICE_VOLUME_SET, data, allow_override=True)

    async def async_media_play(self):
        """Send play command."""
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PLAY)

    async def async_media_pause(self):
        """Send pause command."""
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PAUSE)

    async def async_media_stop(self):
        """Send stop command."""
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PAUSE)

    async def async_media_previous_track(self):
        """Send previous track command."""
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_SKIP_PREVIOUS)

    async def async_media_next_track(self):
        """Send next track command."""
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_SKIP_NEXT)

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Play a piece of media."""
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PLAY)
        # data = {ATTR_MEDIA_CONTENT_TYPE: media_type, ATTR_MEDIA_CONTENT_ID: media_id}
        # await self._async_call_service(SERVICE_PLAY_MEDIA, data)

    async def async_volume_up(self):
        """Turn volume up for media player."""
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_VOLUME_UP)

    async def async_volume_down(self):
        """Turn volume down for media player."""
        async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_VOLUME_DOWN)

    async def async_media_play_pause(self):
        """Play or pause the media player."""
        if self._player_state == STATE_PLAYING:
            async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PAUSE)
        else:
            async_publish(self.hass, self._remote[ATTR_TOPIC], COMMAND_PLAY)

    async def async_update(self):
        """Update state in HA."""
        # for child_name in self._children:
        #     child_state = self.hass.states.get(child_name)
        #     if child_state and child_state.state not in OFF_STATES:
        #         self._child_state = child_state
        #         return
        # self._child_state = None
