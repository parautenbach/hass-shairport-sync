"""Tests for the Shairport Sync media player."""

from __future__ import annotations

import pytest
from homeassistant.components.media_player import (
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_VOLUME_LEVEL,
)
from homeassistant.components.media_player import DOMAIN as MP_DOMAIN
from homeassistant.components.media_player import MediaPlayerState, MediaType
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_ENTITY_PICTURE,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PLAY_PAUSE,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_MEDIA_STOP,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_fire_mqtt_message

from custom_components.shairport_sync import media_player
from custom_components.shairport_sync.media_player import ShairportSyncMediaPlayer

from .conftest import ENTITY_ID, TOPIC

REMOTE_TOPIC = f"{TOPIC}/remote"

# Shairport Sync volume payload: airplay_volume,volume,lowest_volume,highest_volume
VOLUME_HALF = "-15.0,-30.0,-60.0,0.0"


def _published(mqtt_mock) -> list[tuple[str, str]]:
    """Return the (topic, payload) pairs published to the broker."""
    return [c.args[:2] for c in mqtt_mock.async_publish.call_args_list]


def _state(hass: HomeAssistant):
    return hass.states.get(ENTITY_ID)


async def _fire(hass: HomeAssistant, topic: str, payload: str | bytes = "") -> None:
    async_fire_mqtt_message(hass, f"{TOPIC}/{topic}", payload)
    await hass.async_block_till_done()


async def test_initial_state(hass: HomeAssistant, setup_integration) -> None:
    """The player starts idle with no metadata."""
    state = _state(hass)
    assert state.state == MediaPlayerState.IDLE
    assert state.attributes[ATTR_MEDIA_CONTENT_TYPE] == MediaType.MUSIC
    assert ATTR_MEDIA_TITLE not in state.attributes
    assert ATTR_MEDIA_VOLUME_LEVEL not in state.attributes


async def test_subscribes_to_topics(
    hass: HomeAssistant, mqtt_mock, setup_integration
) -> None:
    """All Shairport Sync topics are subscribed to."""
    subscribed = {c.args[0] for c in mqtt_mock.async_subscribe.call_args_list}
    for topic in (
        "play_start",
        "play_resume",
        "play_end",
        "play_flush",
        "active_end",
        "artist",
        "album",
        "title",
        "cover",
        "volume",
    ):
        assert f"{TOPIC}/{topic}" in subscribed


@pytest.mark.parametrize(
    ("topic", "expected"),
    [
        ("play_start", MediaPlayerState.PLAYING),
        ("play_resume", MediaPlayerState.PLAYING),
        ("play_end", MediaPlayerState.PAUSED),
        ("play_flush", MediaPlayerState.PAUSED),
    ],
)
async def test_state_topics(
    hass: HomeAssistant, setup_integration, topic: str, expected: MediaPlayerState
) -> None:
    """Play state messages update the player state."""
    await _fire(hass, topic)
    assert _state(hass).state == expected


async def test_metadata_and_active_end(hass: HomeAssistant, setup_integration) -> None:
    """Metadata is shown while playing and cleared when the session ends."""
    await _fire(hass, "play_start")
    await _fire(hass, "title", "Song")
    await _fire(hass, "artist", "Artist")
    await _fire(hass, "album", "Album")

    state = _state(hass)
    assert state.state == MediaPlayerState.PLAYING
    assert state.attributes[ATTR_MEDIA_TITLE] == "Song"
    assert state.attributes[ATTR_MEDIA_ARTIST] == "Artist"
    assert state.attributes[ATTR_MEDIA_ALBUM_NAME] == "Album"

    await _fire(hass, "active_end")
    state = _state(hass)
    assert state.state == MediaPlayerState.IDLE
    assert ATTR_MEDIA_TITLE not in state.attributes
    assert ATTR_MEDIA_ARTIST not in state.attributes
    assert ATTR_MEDIA_ALBUM_NAME not in state.attributes


async def test_cover_art(hass: HomeAssistant, setup_integration, hass_client) -> None:
    """Cover art is exposed through the media player image proxy."""
    assert ATTR_ENTITY_PICTURE not in _state(hass).attributes

    image = b"\xff\xd8\xff\xe0fake-jpeg"
    await _fire(hass, "cover", image)

    picture = _state(hass).attributes[ATTR_ENTITY_PICTURE]
    client = await hass_client()
    resp = await client.get(picture)
    assert resp.status == 200
    assert resp.content_type == "image/jpeg"
    assert await resp.read() == image


async def test_volume_topic(hass: HomeAssistant, setup_integration) -> None:
    """The volume topic sets the volume level."""
    await _fire(hass, "volume", VOLUME_HALF)
    assert _state(hass).attributes[ATTR_MEDIA_VOLUME_LEVEL] == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("0.0,0.0,-60.0,0.0", 1.0),
        ("-30.0,-60.0,-60.0,0.0", 0.0),
        ("-7.5,-15.0,-60.0,0.0", 0.75),
        # Muted
        ("-144.0,-96.0,-60.0,0.0", 0.0),
        # Clamped
        ("5.0", 1.0),
        ("garbage", 0.0),
        ("", 0.0),
        (None, 0.0),
    ],
)
def test_calculate_volume_level(payload: str | None, expected: float) -> None:
    """Shairport Sync volume payloads map linearly onto [0, 1]."""
    player = ShairportSyncMediaPlayer(None, "name", TOPIC)
    assert player.calculate_volume_level(payload) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("service", "command", "expected_state"),
    [
        (SERVICE_MEDIA_PLAY, "play", MediaPlayerState.PLAYING),
        (SERVICE_MEDIA_PAUSE, "pause", MediaPlayerState.PAUSED),
        (SERVICE_MEDIA_STOP, "stop", MediaPlayerState.IDLE),
        (SERVICE_MEDIA_NEXT_TRACK, "nextitem", MediaPlayerState.IDLE),
        (SERVICE_MEDIA_PREVIOUS_TRACK, "previtem", MediaPlayerState.IDLE),
        (SERVICE_VOLUME_UP, "volumeup", MediaPlayerState.IDLE),
        (SERVICE_VOLUME_DOWN, "volumedown", MediaPlayerState.IDLE),
    ],
)
async def test_remote_commands(
    hass: HomeAssistant,
    mqtt_mock,
    setup_integration,
    service: str,
    command: str,
    expected_state: MediaPlayerState,
) -> None:
    """Services publish the matching command to the remote topic."""
    await hass.services.async_call(
        MP_DOMAIN, service, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    assert _published(mqtt_mock) == [(REMOTE_TOPIC, command)]
    assert _state(hass).state == expected_state


async def test_play_pause_toggle(
    hass: HomeAssistant, mqtt_mock, setup_integration
) -> None:
    """Play/pause toggles based on the current state."""
    for expected_command, expected_state in (
        ("play", MediaPlayerState.PLAYING),
        ("pause", MediaPlayerState.PAUSED),
    ):
        mqtt_mock.async_publish.reset_mock()
        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_MEDIA_PLAY_PAUSE,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        assert _published(mqtt_mock) == [(REMOTE_TOPIC, expected_command)]
        assert _state(hass).state == expected_state


def _simulate_shairport_volume(hass: HomeAssistant, mqtt_mock, start: float) -> None:
    """Make the mocked broker answer volumeup/volumedown like Shairport Sync.

    Each step moves the AirPlay volume by 1/16 of the [-30, 0] range.
    """
    level = {"value": start}
    step = 1 / 16

    async def _publish(topic, payload, *args, **kwargs):
        if topic != REMOTE_TOPIC:
            return
        delta = step if payload == "volumeup" else -step
        level["value"] = max(0.0, min(1.0, level["value"] + delta))
        airplay = (level["value"] - 1) * 30
        hass.loop.call_soon(
            async_fire_mqtt_message, hass, f"{TOPIC}/volume", f"{airplay},0,0,0"
        )

    mqtt_mock.async_publish.side_effect = _publish


@pytest.mark.parametrize(
    ("target", "command", "steps"),
    [(0.75, "volumeup", 4), (0.25, "volumedown", 4), (0.5, None, 0)],
)
async def test_set_volume_level_steps(
    hass: HomeAssistant,
    mqtt_mock,
    setup_integration,
    target: float,
    command: str | None,
    steps: int,
) -> None:
    """Setting the volume steps up/down until the target is reached."""
    await _fire(hass, "volume", VOLUME_HALF)
    mqtt_mock.async_publish.reset_mock()
    _simulate_shairport_volume(hass, mqtt_mock, 0.5)

    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: target},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert _published(mqtt_mock) == [(REMOTE_TOPIC, command)] * steps
    assert _state(hass).attributes[ATTR_MEDIA_VOLUME_LEVEL] == pytest.approx(target)


async def test_set_volume_level_unknown_current(
    hass: HomeAssistant, mqtt_mock, setup_integration
) -> None:
    """Without a known current volume nothing is sent."""
    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: 0.8},
        blocking=True,
    )
    await hass.async_block_till_done()
    mqtt_mock.async_publish.assert_not_called()


async def test_set_volume_level_no_feedback(
    hass: HomeAssistant,
    mqtt_mock,
    setup_integration,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Stepping stops after one command if Shairport Sync never reports back."""
    monkeypatch.setattr(media_player, "VOLUME_FEEDBACK_TIMEOUT", 0.01)
    await _fire(hass, "volume", VOLUME_HALF)
    mqtt_mock.async_publish.reset_mock()

    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: 1.0},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert _published(mqtt_mock) == [(REMOTE_TOPIC, "volumeup")]
    assert "No volume feedback" in caplog.text


async def test_yaml_platform(hass: HomeAssistant, mqtt_mock) -> None:
    """The legacy YAML platform still sets up a player."""
    assert await async_setup_component(
        hass,
        MP_DOMAIN,
        {
            MP_DOMAIN: {
                "platform": "shairport_sync",
                "name": "Yaml Player",
                "topic": "yaml/topic",
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("media_player.yaml_player")
    assert state is not None
    assert state.state == MediaPlayerState.IDLE
