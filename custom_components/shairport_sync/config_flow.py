"""Config flow for Shairport Sync media player."""
from __future__ import annotations

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.components.mqtt.const import CONF_TOPIC
from homeassistant.components.mqtt.util import valid_subscribe_topic
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import DOMAIN


class ShairportConfigFlow(ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input) -> FlowResult:
        errors = {}
        if user_input is not None:
            try:
                valid_subscribe_topic(user_input[CONF_TOPIC])
            except vol.Invalid:
                errors[CONF_TOPIC] = "invalid_subscribe_topic"

            # Build a "unique" ID from the MQTT topic
            topic = user_input.get(CONF_TOPIC)
            id = f"shairport-sync-{topic}"

            # Set ID and fail if already configured
            await self.async_set_unique_id(id)
            self._abort_if_unique_id_configured()

            # Build config data
            data = {
                CONF_ID: id,
                CONF_NAME: user_input.get(CONF_NAME),
                CONF_TOPIC: topic
            }

            # Create a config entry with the config data
            if not errors:
                return self.async_create_entry(title=f"{DOMAIN} {topic}", data=data)

        user_input = user_input or {}

        data_schema = vol.Schema({
            vol.Required(CONF_NAME): cv.string,
            vol.Required(CONF_TOPIC,
                         description={"suggested_value": user_input.get(CONF_TOPIC, "Shairport")}): cv.string,
        })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
