"""The 2dehands integration."""

import logging
from typing import Final

from homeassistant import config_entries, core
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import TwoDehandsCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN: Final = "2dehands"
PLATFORMS: Final = ["sensor"]


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the 2dehands integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up 2dehands from a config entry."""
    _LOGGER.debug("Setting up 2dehands integration")

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    if not username or not password:
        _LOGGER.error("Missing username or password in configuration")
        return False

    session = async_get_clientsession(hass)

    coordinator = TwoDehandsCoordinator(
        hass=hass,
        session=session,
        username=username,
        password=password,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading 2dehands integration")

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        await coordinator.async_logout()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)