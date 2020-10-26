"""Support for Nanoleaf Lights."""

import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    SUPPORT_EFFECT,
    SUPPORT_TRANSITION,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.util import color as color_util
from homeassistant.util.color import (
    color_temperature_mired_to_kelvin as mired_to_kelvin,
)

from pynanoleaf import Nanoleaf, Unavailable

from .const import DOMAIN, DATA_NAME, DATA_NANOLEAF

_LOGGER = logging.getLogger(__name__)

ICON_TRIANGLE = "mdi:triangle-outline"
ICON_SQUARE = "mdi:square-outline"
ICON_HEXAGON = "mdi:hexagon-outline"

SUPPORT_NANOLEAF = (
    SUPPORT_BRIGHTNESS
    | SUPPORT_COLOR
    | SUPPORT_COLOR_TEMP
    | SUPPORT_EFFECT
    | SUPPORT_TRANSITION
)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities
):
    """Set up Nanoleaf lights."""
    data = hass.data[DOMAIN][config.entry_id]
    nanoleaf = data[DATA_NANOLEAF]
    name = data[DATA_NAME]

    async_add_entities([NanoleafLight(nanoleaf, name)], True)


class NanoleafLight(LightEntity):
    """Representation of a Nanoleaf Light."""

    def __init__(self, light: Nanoleaf, name: str):
        """Initialize an Nanoleaf light."""
        self._unique_id = None
        self._available = True
        self._brightness = None
        self._color_temp = None
        self._effect = None
        self._effects_list = None
        self._firmwareVersion = None
        self._light = light
        self._manufacturer = None
        self._model = None
        self._name = name
        self._hs_color = None
        self._state = None

    @property
    def available(self):
        """Return availability."""
        return self._available

    @property
    def brightness(self):
        """Return the brightness of the light."""
        if self._brightness is not None:
            return int(self._brightness * 2.55)
        return None

    @property
    def color_temp(self):
        """Return the current color temperature."""
        if self._color_temp is not None:
            return color_util.color_temperature_kelvin_to_mired(self._color_temp)
        return None

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": self._manufacturer,
            "model": self._model,
            "sw_version": self._firmwareVersion,
        }

    @property
    def effect(self):
        """Return the current effect."""
        return self._effect

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return self._effects_list

    @property
    def min_mireds(self):
        """Return the coldest color_temp that this light supports."""
        return 154

    @property
    def max_mireds(self):
        """Return the warmest color_temp that this light supports."""
        return 833

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        if self._model == "NL29":
            return ICON_SQUARE
        elif self._model == "NL42":
            return ICON_HEXAGON
        return ICON_TRIANGLE

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def hs_color(self):
        """Return the color in HS."""
        return self._hs_color

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_NANOLEAF

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        hs_color = kwargs.get(ATTR_HS_COLOR)
        color_temp_mired = kwargs.get(ATTR_COLOR_TEMP)
        effect = kwargs.get(ATTR_EFFECT)
        transition = kwargs.get(ATTR_TRANSITION)

        if hs_color:
            hue, saturation = hs_color
            self._light.hue = int(hue)
            self._light.saturation = int(saturation)
        if color_temp_mired:
            self._light.color_temperature = mired_to_kelvin(color_temp_mired)

        if transition:
            if brightness:  # tune to the required brightness in n seconds
                self._light.brightness_transition(
                    int(brightness / 2.55), int(transition)
                )
            else:  # If brightness is not specified, assume full brightness
                self._light.brightness_transition(100, int(transition))
        else:  # If no transition is occurring, turn on the light
            self._light.on = True
            if brightness:
                self._light.brightness = int(brightness / 2.55)

        if effect:
            if effect not in self._effects_list:
                raise ValueError(
                    f"Attempting to apply effect not in the effect list: '{effect}'"
                )
            self._light.effect = effect

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        transition = kwargs.get(ATTR_TRANSITION)
        if transition:
            self._light.brightness_transition(0, int(transition))
        else:
            self._light.on = False

    def update(self):
        """Fetch new state data for this light."""

        try:
            info = self._light.info
            self._available = True

            self._firmwareVersion = info["firmwareVersion"]
            self._manufacturer = info["manufacturer"]
            self._model = info["model"]
            self._unique_id = info["serialNo"]

            self._brightness = info["state"]["brightness"]["value"]
            self._effects_list = info["effects"]["effectsList"]
            # Nanoleaf api returns non-existent effect named "*Solid*" when light set to solid color.
            # This causes various issues with scening (see https://github.com/home-assistant/core/issues/36359).
            # Until fixed at the library level, we should ensure the effect exists before saving to light properties
            self._effect = (
                info["effects"]["select"]
                if info["effects"]["select"] in self._effects_list
                else None
            )
            if self._effect is None:
                self._color_temp = info["state"]["ct"]["value"]
                self._hs_color = (
                    info["state"]["hue"]["value"],
                    info["state"]["sat"]["value"],
                )
            else:
                self._color_temp = None
                self._hs_color = None
            self._state = info["state"]["on"]["value"]
        except Unavailable as err:
            _LOGGER.error("Could not update status for %s (%s)", self.name, err)
            self._available = False
