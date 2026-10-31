"""Tests for setting up and unloading Shairport Sync."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.shairport_sync.const import DOMAIN

from .conftest import ENTITY_ID, TOPIC


async def test_setup_and_unload(hass: HomeAssistant, setup_integration) -> None:
    """The entry loads, creates the entity and device, and unloads cleanly."""
    entry = setup_integration
    assert entry.state is ConfigEntryState.LOADED

    entity = er.async_get(hass).async_get(ENTITY_ID)
    assert entity is not None
    assert entity.unique_id == f"shairport-sync-{TOPIC}"

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, TOPIC), entry.entry_id
    )
    assert device is not None
    assert device.manufacturer == "mikebrady"
    assert entity.device_id == device.id

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


async def test_reload(hass: HomeAssistant, setup_integration) -> None:
    """The entry can be reloaded."""
    entry = setup_integration
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(ENTITY_ID) is not None
