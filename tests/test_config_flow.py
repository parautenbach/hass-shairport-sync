"""Tests for the Shairport Sync config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.components.mqtt.const import CONF_TOPIC
from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.shairport_sync.const import DOMAIN

from .conftest import NAME, TOPIC


async def test_user_flow_creates_entry(hass: HomeAssistant, mqtt_mock) -> None:
    """A valid name and topic create a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: NAME, CONF_TOPIC: TOPIC}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"{DOMAIN} {TOPIC}"
    assert result["data"] == {
        CONF_ID: f"shairport-sync-{TOPIC}",
        CONF_NAME: NAME,
        CONF_TOPIC: TOPIC,
    }
    assert result["result"].unique_id == f"shairport-sync-{TOPIC}"


async def test_user_flow_invalid_topic(hass: HomeAssistant, mqtt_mock) -> None:
    """An invalid MQTT subscribe topic shows an error and allows a retry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: NAME, CONF_TOPIC: "bad/#/topic"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TOPIC: "invalid_subscribe_topic"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: NAME, CONF_TOPIC: TOPIC}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant, mqtt_mock, config_entry
) -> None:
    """Configuring the same topic twice aborts."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Other", CONF_TOPIC: TOPIC}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
