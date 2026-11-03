"""Fixtures for Shairport Sync tests."""

from __future__ import annotations

import pytest
from homeassistant.components.mqtt.const import CONF_TOPIC
from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shairport_sync.const import DOMAIN

TOPIC = "shairport"
NAME = "Living Room"
ENTITY_ID = "media_player.living_room"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield


@pytest.fixture(autouse=True)
def expected_lingering_timers() -> bool:
    """Allow the MQTT client's misc loop timer to outlive a test.

    The mocked paho client never closes its socket, so the timer is not
    cancelled. Core makes the same exemption for its own MQTT tests.
    """
    return True


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry as created by the config flow."""
    uid = f"shairport-sync-{TOPIC}"
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"{DOMAIN} {TOPIC}",
        unique_id=uid,
        data={CONF_ID: uid, CONF_NAME: NAME, CONF_TOPIC: TOPIC},
    )


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, mqtt_mock, config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the integration with a mocked MQTT broker."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
