"""A Shairport Sync media player custom component for HASS using MQTT."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up a Shairport Sync device from a config entry."""

    # Create platform entries
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Reload entry when its updated
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a Shairport Sync device."""
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload a Shairport Sync device."""
    await hass.config_entries.async_reload(config_entry.entry_id)
