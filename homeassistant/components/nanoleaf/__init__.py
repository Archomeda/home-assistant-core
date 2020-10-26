"""The nanoleaf component."""

import logging

from homeassistant.const import (
    CONF_HOST,
    CONF_ID,
    CONF_PORT,
    CONF_NAME,
    CONF_TOKEN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from pynanoleaf import Nanoleaf, InvalidToken, Unavailable

from .const import DOMAIN, PLATFORMS, DATA_NAME, DATA_NANOLEAF

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up the Nanoleaf component."""
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up Nanoleaf config."""
    name = config.data[CONF_NAME]
    host = config.data[CONF_HOST]
    port = config.data[CONF_PORT]
    token = config.data[CONF_TOKEN]
    nanoleaf = Nanoleaf(host, port=port, token=token)

    hass.data[DOMAIN][config.entry_id] = {
        DATA_NANOLEAF: nanoleaf,
        DATA_NAME: name,
    }

    _LOGGER.debug(f"Initializing Nanoleaf {name}")

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config, platform)
        )

    return True


async def async_remove_entry(hass: HomeAssistant, config: ConfigEntry) -> None:
    """Clean up Nanoleaf config."""
    name = config.data[CONF_NAME]
    host = config.data[CONF_HOST]
    port = config.data[CONF_PORT]
    token = config.data[CONF_TOKEN]
    nanoleaf = Nanoleaf(host, port=port, token=token)

    # Try to delete the token from the nanoleaf
    try:
        _LOGGER.debug(f"Unregistering Nanoleaf {name}")

        await hass.async_add_executor_job(nanoleaf.delete_token)
    except InvalidToken:
        _LOGGER.error(
            f"Failed to unregister token from Nanoleaf {name} with token {token}. Token is invalid. Try calling DELETE http://{host}:{port}/api/v1/{token} manually."
        )
    except Unavailable:
        _LOGGER.error(
            f"Failed to unregister token from Nanoleaf {name} with token {token}. The device is unavailable. Try calling DELETE http://{host}:{port}/api/v1/{token} manually."
        )
