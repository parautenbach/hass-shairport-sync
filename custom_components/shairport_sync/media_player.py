"""For media players that are controlled via MQTT."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import Callable
from typing import cast

import probatio

# MediaPlayerDeviceClass is defined here before HA 2026.10. Since then it lives in
# media_player.const and is re-exported here, but not declared public (for mypy).
from homeassistant.components.media_player import (  # type: ignore[attr-defined]
    PLATFORM_SCHEMA,
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.components.mqtt import async_publish, async_subscribe
from homeassistant.components.mqtt.const import CONF_TOPIC
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.components.mqtt.util import valid_publish_topic
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN, Command, TopLevelTopic

_LOGGER = logging.getLogger(__name__)

# Default values for volume control

# Volume default step (1/16), updated on the fly
VOLUME_DEFAULT_STEP = 0.0625
# Infinite loop protection
VOLUME_MAX_STEPS = 40
# Seconds to wait for volume feedback from shairport-sync before giving up
VOLUME_FEEDBACK_TIMEOUT = 2.0

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        probatio.Required(CONF_NAME): cv.string,
        probatio.Required(CONF_TOPIC): valid_publish_topic,
    },
    extra=probatio.REMOVE_EXTRA,
)

SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_SET
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the MQTT media players."""
    _LOGGER.debug(config)

    async_add_entities(
        [
            ShairportSyncMediaPlayer(
                hass,
                config[CONF_NAME],
                config[CONF_TOPIC],
            )
        ]
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Setup the media player platform for Shairport Sync."""

    # Get config from entry
    config = config_entry.data

    async_add_entities(
        [
            ShairportSyncMediaPlayer(
                hass,
                config[CONF_NAME],
                config[CONF_TOPIC],
            )
        ]
    )


class ShairportSyncMediaPlayer(MediaPlayerEntity):
    """Representation of an MQTT-controlled media player."""

    def __init__(self, hass: HomeAssistant, name: str, topic: str) -> None:
        """Initialize the MQTT media device."""
        _LOGGER.debug("Initialising %s", name)
        self.hass = hass
        self._name = name
        self._base_topic = topic
        self._remote_topic = f"{self._base_topic}/{TopLevelTopic.REMOTE}"
        self._player_state = MediaPlayerState.IDLE
        self._title: str | None = None
        self._artist: str | None = None
        self._album: str | None = None
        self._media_image: bytes | None = None
        self._subscriptions: list[CALLBACK_TYPE] = []
        self._volume_level: float | None = None
        self._idle_task: asyncio.Task[None] | None = None
        self._volume_target: float | None = None
        self._volume_task: asyncio.Task[None] | None = None
        self._volume_event = asyncio.Event()
        self._volume_step = VOLUME_DEFAULT_STEP

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        await self._subscribe_to_topics()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        _LOGGER.debug("Removing %s subscriptions", len(self._subscriptions))
        for unsubscribe in self._subscriptions:
            unsubscribe()
        if self._volume_task:
            self._volume_task.cancel()
            self._volume_task = None

    def _set_state(self, state: MediaPlayerState) -> None:
        """Update the player state."""

        _LOGGER.debug("Setting state to '%s'.", state)
        self._player_state = state

        # Clear metadata in idle state so media card doesn't display stale data
        if state == MediaPlayerState.IDLE:
            self._title = None
            self._artist = None
            self._album = None
            self._media_image = None

        self.async_write_ha_state()

    def calculate_volume_level(self, volume: str | None) -> float:
        """Calculate the volume level from a string."""
        if volume is None:
            return 0.0
        try:
            # Shairport Sync publishes the volume topic as
            # "airplay_volume,volume,lowest_volume,highest_volume"
            # aka "airplay_volume,mixer_volume_db,lowest_db,highest_db"
            volume_parts = volume.split(",")
            volume_level = float(volume_parts[0])
            # Map the AirPlay range [-30.0, 0.0] linearly to [0.0, 1.0]
            calculated_volume = (volume_level / 30) + 1
            # Clamp to [0.0, 1.0], this also maps the "muted" value (-144.0) to 0.0
            calculated_volume = max(0.0, min(1.0, calculated_volume))
            _LOGGER.debug("Calculated volume level: %s", calculated_volume)
            return calculated_volume
        except (ValueError, IndexError) as e:
            _LOGGER.error("Error calculating volume level: %s", e)
            return 0.0

    async def _subscribe_to_topics(self) -> None:
        """(Re)Subscribe to topics."""

        @callback
        def play_started(_: ReceiveMessage) -> None:
            """Handle the play MQTT message."""
            _LOGGER.debug("Play started")
            if self._idle_task:
                self._idle_task.cancel()
                self._idle_task = None
            self._set_state(MediaPlayerState.PLAYING)

        @callback
        def play_ended(_: ReceiveMessage) -> None:
            """Handle the pause MQTT message."""
            _LOGGER.debug("Play ended")
            self._set_state(MediaPlayerState.PAUSED)

        @callback
        def active_ended(_: ReceiveMessage) -> None:
            """Handle the active ended MQTT message."""
            _LOGGER.debug("Active ended")
            self._set_state(MediaPlayerState.IDLE)

        def set_metadata(attr: str) -> Callable[[ReceiveMessage], None]:
            """Construct a callback that sets the desired metadata attribute."""

            @callback
            def _callback(msg: ReceiveMessage) -> None:
                setattr(self, f"_{attr}", msg.payload)
                _LOGGER.debug("New %s: %s", attr, msg.payload)
                self.async_write_ha_state()

            return _callback

        @callback
        def artwork_updated(message: ReceiveMessage) -> None:
            """Handle the artwork updated MQTT message."""
            # Subscribed without an encoding, so the payload is raw bytes
            image = cast(bytes, message.payload)
            # https://en.wikipedia.org/wiki/Magic_number_%28programming%29
            # https://en.wikipedia.org/wiki/List_of_file_signatures
            header = " ".join(f"{b:02X}" for b in image[:4])
            _LOGGER.debug("New artwork (%s bytes); header: %s", len(image), header)
            self._media_image = image
            self.async_write_ha_state()

        @callback
        def set_metadata_volume_level(msg: ReceiveMessage) -> None:
            """Handle the volume MQTT message."""
            # Subscribed with UTF-8 encoding, so the payload is decoded text
            calculated_volume = self.calculate_volume_level(cast(str, msg.payload))
            _LOGGER.debug("New volume level: %s", calculated_volume)
            self._volume_level = calculated_volume
            self._volume_event.set()
            self.async_write_ha_state()

        topic_map: dict[
            TopLevelTopic, tuple[Callable[[ReceiveMessage], None], str | None]
        ] = {
            TopLevelTopic.PLAY_START: (play_started, "utf-8"),
            TopLevelTopic.PLAY_RESUME: (play_started, "utf-8"),
            TopLevelTopic.PLAY_END: (play_ended, "utf-8"),
            TopLevelTopic.PLAY_FLUSH: (play_ended, "utf-8"),
            TopLevelTopic.ACTIVE_END: (active_ended, "utf-8"),
            TopLevelTopic.ARTIST: (set_metadata("artist"), "utf-8"),
            TopLevelTopic.ALBUM: (set_metadata("album"), "utf-8"),
            TopLevelTopic.TITLE: (set_metadata("title"), "utf-8"),
            TopLevelTopic.COVER: (artwork_updated, None),
            TopLevelTopic.VOLUME: (set_metadata_volume_level, "utf-8"),
        }

        for top_level_topic, (topic_callback, encoding) in topic_map.items():
            topic = f"{self._base_topic}/{top_level_topic}"
            _LOGGER.debug(
                "Subscribing to topic %s with callback %s",
                topic,
                topic_callback.__name__,
            )
            subscription = await async_subscribe(
                self.hass, topic, topic_callback, encoding=encoding
            )
            self._subscriptions.append(subscription)

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def unique_id(self) -> str:
        return f"shairport-sync-{self._base_topic}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._base_topic)},
            name=self.name,
            manufacturer="mikebrady",
        )

    @property
    def name(self) -> str:
        """Return the name of the player."""
        _LOGGER.debug("Getting name: %s", self._name)
        return self._name

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the current state of the media player."""
        _LOGGER.debug("Getting state: %s", self._player_state)
        return self._player_state

    @property
    def media_content_type(self) -> MediaType | None:
        """Return the content type of currently playing media."""
        _LOGGER.debug("Getting media content type: %s", MediaType.MUSIC)
        return MediaType.MUSIC

    @property
    def media_title(self) -> str | None:
        """Title of current playing media."""
        _LOGGER.debug("Getting media title: %s", self._title)
        return self._title

    @property
    def media_artist(self) -> str | None:
        """Artist of current playing media, music track only."""
        _LOGGER.debug("Getting media artist: %s", self._artist)
        return self._artist

    @property
    def media_album_name(self) -> str | None:
        """Album of current playing media, music track only."""
        _LOGGER.debug("Getting media album: %s", self._album)
        return self._album

    @property
    def media_image_hash(self) -> str | None:
        """Hash value for the media image."""
        if self._media_image:
            image_hash = hashlib.md5(self._media_image).hexdigest()
            _LOGGER.debug("Media image hash: %s", image_hash)
            return image_hash
        return None

    @property
    def volume_level(self) -> float | None:
        """Return the volume level of the media player."""
        _LOGGER.debug("Getting volume level: %s", self._volume_level)
        return self._volume_level

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
        return SUPPORTED_FEATURES

    @property
    def device_class(self) -> MediaPlayerDeviceClass:
        return MediaPlayerDeviceClass.SPEAKER

    async def _send_remote_command(self, command: Command) -> None:
        """Send a command to the remote control topic."""
        _LOGGER.debug("Sending '%s' command", command)
        await async_publish(self.hass, self._remote_topic, command)

    async def _send_command_update_state(
        self, command: Command, state: MediaPlayerState
    ) -> None:
        """Send the command and update local state."""
        await self._send_remote_command(command)
        self._set_state(state)

    async def async_media_play(self) -> None:
        """Send play command."""
        await self._send_command_update_state(Command.PLAY, MediaPlayerState.PLAYING)

    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self._send_command_update_state(Command.PAUSE, MediaPlayerState.PAUSED)

    async def async_media_stop(self) -> None:
        """Send stop command."""
        await self._send_command_update_state(Command.STOP, MediaPlayerState.IDLE)

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        await self._send_remote_command(Command.SKIP_PREVIOUS)

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._send_remote_command(Command.SKIP_NEXT)

    async def async_volume_up(self) -> None:
        """Turn volume up for media player."""
        await self._send_remote_command(Command.VOLUME_UP)

    async def async_volume_down(self) -> None:
        """Turn volume down for media player."""
        await self._send_remote_command(Command.VOLUME_DOWN)

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume by stepping up/down until the target is reached."""
        _LOGGER.debug("Setting volume level to %s", volume)
        self._volume_target = max(0.0, min(1.0, volume))

        if self._volume_task and not self._volume_task.done():
            return
        self._volume_task = self.hass.async_create_task(self._async_adjust_volume())

    async def _async_adjust_volume(self) -> None:
        """Step the volume towards self._volume_target using volumeup/volumedown."""
        for _ in range(VOLUME_MAX_STEPS):
            current = self._volume_level
            target = self._volume_target
            if current is None or target is None:
                _LOGGER.debug("Unknown current volume, cannot adjust")
                return

            diff = target - current
            if abs(diff) < self._volume_step / 2:
                _LOGGER.debug("Volume target reached (%s ~ %s)", current, target)
                return

            self._volume_event.clear()
            await self._send_remote_command(
                Command.VOLUME_UP if diff > 0 else Command.VOLUME_DOWN
            )

            try:
                await asyncio.wait_for(
                    self._volume_event.wait(), timeout=VOLUME_FEEDBACK_TIMEOUT
                )
            except TimeoutError:
                _LOGGER.warning("No volume feedback from shairport-sync, giving up")
                return

            new = self._volume_level
            if new is None:
                return
            observed = abs(new - current)
            if observed == 0:
                _LOGGER.debug("Volume did not change, stopping")
                return
            if observed <= 0.25:
                self._volume_step = observed

    async def async_media_play_pause(self) -> None:
        """Play or pause the media player."""
        _LOGGER.debug(
            "Sending toggle play/pause command; currently %s", self._player_state
        )
        if self._player_state == MediaPlayerState.PLAYING:
            await self._send_command_update_state(
                Command.PAUSE, MediaPlayerState.PAUSED
            )
        else:
            await self._send_command_update_state(
                Command.PLAY, MediaPlayerState.PLAYING
            )

    async def async_get_media_image(self) -> tuple[bytes | None, str | None]:
        """Fetch the image of the currently playing media."""
        _LOGGER.debug("Getting media image")
        if self._media_image:
            return (self._media_image, "image/jpeg")
        return (None, None)
