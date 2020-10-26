"""Config flow for nanoleaf."""

import logging
from typing import Any, Dict

from homeassistant import config_entries
from homeassistant.const import (
    CONF_TYPE,
    CONF_HOST,
    CONF_PORT,
    CONF_ID,
    CONF_NAME,
    CONF_TOKEN,
)
from homeassistant.config_entries import ConfigEntry

from pynanoleaf import Nanoleaf, NotAuthorizingNewTokens, Unavailable

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class NanoleafConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    def __init__(self):
        """Set up the instance."""
        self.discovery_info = {}

    async def async_step_zeroconf(self, discovery_info: ConfigEntry):
        """Handle zeroconf discovery."""
        _LOGGER.debug(discovery_info)

        # Get all discovery properties
        host = discovery_info[CONF_HOST]
        port = discovery_info[CONF_PORT]
        zctype = discovery_info[CONF_TYPE]
        name = discovery_info[CONF_NAME].replace(f".{zctype}", "")
        id = discovery_info["properties"]["id"]
        model = discovery_info["properties"]["md"]
        version = discovery_info["properties"]["srcvers"]

        _LOGGER.debug(
            f"Discovered Nanoleaf {name} on {host}:{port} ({model}, {version})"
        )
        self.discovery_info.update(
            {
                CONF_HOST: host,
                CONF_PORT: port,
                CONF_ID: id,
                CONF_NAME: name,
            }
        )

        # Detect duplicates
        await self.async_set_unique_id(id)
        self._abort_if_unique_id_configured()

        # pylint: disable=no-member # https://github.com/PyCQA/pylint/issues/3167
        self.context.update({"title_placeholders": self.discovery_info})

        # Continue to register
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: ConfigEntry = None
    ) -> Dict[str, Any]:
        """Handle the zeroconf discovery pairing with a nanoleaf device."""
        errors = {}

        # If the user has not pressed the save button,
        # show the information "form" on how to pair the detected nanoleaf instead
        if user_input is None:
            return await self._async_show_zeroconf_form(errors)

        nanoleaf = Nanoleaf(
            self.discovery_info[CONF_HOST],
            port=self.discovery_info[CONF_PORT],
        )

        # Try to connect to the nanoleaf and get a token
        try:
            await self.hass.async_add_executor_job(nanoleaf.authorize)
        except NotAuthorizingNewTokens:
            errors["base"] = f"failed_to_request_token"
        except Unavailable:
            errors["base"] = f"cannot_connect"
        if errors:
            return await self._async_show_zeroconf_form(errors)

        data = self.discovery_info
        data[CONF_TOKEN] = nanoleaf.token

        _LOGGER.debug(
            f"Registered Nanoleaf {data[CONF_NAME]} with token {data[CONF_TOKEN]}"
        )

        # Create device
        return await self._entry_from_data(data)

    async def _async_show_zeroconf_form(self, errors: Dict) -> Dict[str, Any]:
        """Show the zeroconf discovery form."""
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders=self.discovery_info,
            errors=errors,
        )

    async def _entry_from_data(self, data):
        """Create an entry from data."""
        return self.async_create_entry(title=data[CONF_NAME], data=data)
