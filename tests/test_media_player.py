"""Test the media player."""

# import asyncio
import uuid

from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.async_mock import AsyncMock
from pytest_homeassistant_custom_component.common import MockConfigEntry

from shairport_sync import media_player


async def test_async_add_entities(hass):
    """Test that the player gets added."""
    mock_async_add_entities = AsyncMock()
    await media_player.async_setup_platform(hass, {}, mock_async_add_entities)
    assert mock_async_add_entities.called


async def test_media_player_init(hass):
    """Test that the player gets initialized properly."""
    expected_name = uuid.uuid1().hex
    random_topic = f"no/such/topic/{uuid.uuid1().hex}/"
    player = media_player.ShairportSyncMediaPlayer(hass, expected_name, random_topic)
    assert player.name == expected_name
    assert player.state == "paused"


async def test_async_added_to_hass(hass, mqtt_mock):
    """Test that the player subscribed to all topics."""
    # components/mqtt/test_common.py:
    # async def help_test_entity_id_update_subscriptions
    random_name = "Random Name"
    expected_base_topic = "expected/topic"
    player = media_player.ShairportSyncMediaPlayer(
        hass, random_name, expected_base_topic
    )
    await player.async_added_to_hass()
    assert mqtt_mock.async_subscribe.call_count == 5
    for (_, (actual_topic, _, _, _), _) in mqtt_mock.async_subscribe.mock_calls:
        assert actual_topic.startswith(expected_base_topic)

    # state = hass.states.get("media_player.random_name")
    # assert state is not None
    # assert state.state == "paused"


# async def test_async_media_play(hass, mqtt_mock):
async def test_1(hass, mqtt_mock):
    """
    Test that sending a play command from the player sends it via MQTT.

    Even though mqtt_mock works fine for subscriptions (in test_async_added_to_hass)
    it doesn't seem like it's invoked when calling e.g. the play function.
    """
    random_name = "Random Name"
    expected_base_topic = "expected/topic"
    player = media_player.ShairportSyncMediaPlayer(
        hass, random_name, expected_base_topic
    )

    # fails
    # state = hass.states.get("media_player.test")
    # assert state is not None

    # from the class under testing:
    # async def async_media_play(self):
    #     """Send play command."""
    #     _LOGGER.debug("Sending play command")
    #     async_publish(self.hass, self._remote_topic, COMMAND_PLAY)
    await player.async_media_play()

    # alternative invocation seen in core tests
    # asyncio.run_coroutine_threadsafe(
    #     player.async_media_play_pause(), hass.loop
    # ).result()

    # fails
    assert mqtt_mock.async_publish.called


async def test_2(hass):
    """Using async_setup_component doesn't seem to work as there is no state object."""
    config = {"platform": "shairport_sync", "name": "Test", "topic": "expected/topic"}
    result = await async_setup_component(hass, "media_player", config)
    await hass.async_block_till_done()
    assert result

    state = hass.states.get("media_player.test")
    # fails
    assert state is not None


async def test_3(hass):
    """Using async_setup_platform doesn't seem to work as there is no state object."""
    mock_async_add_entities = AsyncMock()
    config = {"platform": "shairport_sync", "name": "Test", "topic": "expected/topic"}
    # how do i get the player instance and if i can't, how can i call it's members?
    await media_player.async_setup_platform(hass, config, mock_async_add_entities)
    assert mock_async_add_entities.called

    state = hass.states.get("media_player.test")
    # fails
    assert state is not None


async def test_4(hass):
    """
    Using add_to_hass and async_setup doesn't seem to work as there is no state object.

    _I think_ async_setup is specific to config flow.
    """
    entry = MockConfigEntry(
        domain="media_player",
        data={"platform": "shairport_sync", "name": "Test", "topic": "expected/topic"},
    )

    entry.add_to_hass(hass)
    # is this the right method to call?
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("media_player.test")
    # fails
    assert state is not None


# copied from nwsradar/test_no_loop
async def test_5(hass):
    """Test that nws set up with config yaml."""
    entry = MockConfigEntry(
        domain="media_player",
        data={"platform": "shairport_sync", "name": "Test", "topic": "expected/topic"},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids("media_player")) == 1
    assert hass.states.async_entity_ids("media_player")[0] == "media_player.test"
