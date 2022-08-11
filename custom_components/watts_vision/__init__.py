"""Watts Vision Component."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import API_CLIENT, DOMAIN, SCAN_INTERVAL
from .watts_api import WattsApi

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Watts Vision from a config entry."""
    _LOGGER.debug("Set up Watts Vision")
    hass.data.setdefault(DOMAIN, {})

    client = WattsApi(hass, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    _LOGGER.debug("Get login token")
    await hass.async_add_executor_job(client.getLoginToken)
    _LOGGER.debug("Load data")
    await hass.async_add_executor_job(client.loadData)

    hass.data[DOMAIN][API_CLIENT] = client

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    async def refresh_devices(event_time):
        _LOGGER.debug("refresh login token")
        await hass.async_add_executor_job(client.getLoginToken)
        _LOGGER.debug("reload devices")
        await hass.async_add_executor_job(client.reloadDevices)

    async_track_time_interval(hass, refresh_devices, SCAN_INTERVAL)

    return True
