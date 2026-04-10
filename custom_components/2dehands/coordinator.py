"""Data coordinator for 2dehands integration."""

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)


class TwoDehandsCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from 2dehands."""

    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession, username: str, password: str, update_interval: timedelta = SCAN_INTERVAL):
        """Initialize the coordinator."""
        super().__init__(hass, _LOGGER, name="2dehands", update_interval=update_interval)
        self.session = session
        self.username = username
        self.password = password
        self._auth_token = None
        self.base_url = "https://www.2dehands.be"
        self.api_url = "https://api.2dehands.be"

    async def _async_authenticate(self) -> bool:
        """Authenticate with 2dehands service using username and password."""
        try:
            # Prepare login payload
            login_data = {
                "username": self.username,
                "password": self.password,
            }

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            # Make login request to 2dehands API
            async with self.session.post(
                f"{self.api_url}/login",
                json=login_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._auth_token = data.get("token") or data.get("access_token")
                    _LOGGER.debug("Successfully authenticated with 2dehands")
                    return True
                else:
                    error_msg = await response.text()
                    _LOGGER.error(f"Authentication failed with status {response.status}: {error_msg}")
                    return False

        except asyncio.TimeoutError:
            _LOGGER.error("Authentication request timed out")
            raise UpdateFailed("Authentication request timed out")
        except Exception as e:
            _LOGGER.error(f"Authentication error: {e}")
            raise UpdateFailed(f"Authentication failed: {e}")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from 2dehands."""
        try:
            # Authenticate if not already authenticated
            if not self._auth_token:
                auth_success = await self._async_authenticate()
                if not auth_success:
                    raise UpdateFailed("Failed to authenticate with 2dehands")

            # Prepare headers with authentication
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            if self._auth_token:
                headers["Authorization"] = f"Bearer {self._auth_token}"

            # Fetch sold items data
            async with self.session.get(
                f"{self.api_url}/user/sold-items",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    # Token expired, re-authenticate
                    _LOGGER.info("Token expired, re-authenticating")
                    self._auth_token = None
                    auth_success = await self._async_authenticate()
                    if not auth_success:
                        raise UpdateFailed("Re-authentication failed")
                    # Retry the request
                    return await self._async_update_data()

                response.raise_for_status()
                data = await response.json()

                # Parse the response to extract items sold count
                items_count = self._parse_items_sold(data)
                _LOGGER.debug(f"Fetched {items_count} sold items from 2dehands")

                return {
                    "items_sold": items_count,
                    "raw_data": data,
                }

        except asyncio.TimeoutError:
            raise UpdateFailed("Request to 2dehands timed out")
        except aiohttp.ClientError as e:
            raise UpdateFailed(f"Connection error: {e}")
        except Exception as e:
            raise UpdateFailed(f"Failed to fetch data from 2dehands: {e}")

    @staticmethod
    def _parse_items_sold(data: Dict[str, Any]) -> int:
        """Parse items sold count from API response."""
        try:
            if isinstance(data, dict):
                # Try common response structures
                if "count" in data:
                    return int(data["count"])
                if "items" in data:
                    return len(data["items"])
                if "total" in data:
                    return int(data["total"])
                # Try nested structures
                if "data" in data:
                    return TwoDehandsCoordinator._parse_items_sold(data["data"])
            elif isinstance(data, list):
                return len(data)
            return 0
        except (ValueError, TypeError, KeyError):
            _LOGGER.warning("Could not parse items sold count from response")
            return 0

    async def async_logout(self) -> None:
        """Logout from 2dehands service."""
        if self._auth_token:
            try:
                headers = {
                    "Authorization": f"Bearer {self._auth_token}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
                await self.session.post(
                    f"{self.api_url}/logout",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5),
                )
                self._auth_token = None
                _LOGGER.debug("Successfully logged out from 2dehands")
            except Exception as e:
                _LOGGER.warning(f"Logout error: {e}")
