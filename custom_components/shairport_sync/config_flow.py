"""Config flow for Shairport Sync media player."""

from __future__ import annotations

from typing import Any

import homeassistant.helpers.config_validation as cv
import probatio
from homeassistant.components.mqtt.const import CONF_TOPIC
from homeassistant.components.mqtt.util import valid_subscribe_topic
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ID, CONF_NAME

from .const import DOMAIN


class ShairportConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Shairport Sync."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                valid_subscribe_topic(user_input[CONF_TOPIC])
            except probatio.Invalid:
                errors[CONF_TOPIC] = "invalid_subscribe_topic"

            # Build a "unique" ID from the MQTT topic
            topic = user_input.get(CONF_TOPIC)
            uid = f"shairport-sync-{topic}"

            # Set ID and fail if already configured
            await self.async_set_unique_id(uid)
            self._abort_if_unique_id_configured()

            # Build config data
            data = {
                CONF_ID: uid,
                CONF_NAME: user_input.get(CONF_NAME),
                CONF_TOPIC: topic,
            }

            # Create a config entry with the config data
            if not errors:
                return self.async_create_entry(title=f"{DOMAIN} {topic}", data=data)

        user_input = user_input or {}

        data_schema = probatio.Schema(
            {
                probatio.Required(CONF_NAME): cv.string,
                probatio.Required(
                    CONF_TOPIC,
                    description={
                        "suggested_value": user_input.get(CONF_TOPIC, "Shairport")
                    },
                ): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
