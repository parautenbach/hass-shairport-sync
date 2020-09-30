"""Test the media player."""

import uuid

from pytest_homeassistant_custom_component.async_mock import AsyncMock

from shairport_sync import media_player

# https://docs.pytest.org/en/stable/fixture.html#fixtures
# for mqtt


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
