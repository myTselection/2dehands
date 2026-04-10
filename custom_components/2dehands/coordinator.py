import asyncio
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

class TwoDehandsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession, update_interval: int):
        super().__init__(hass, _LOGGER, name="2dehands", update_interval=update_interval)
        self.session = session

    async def _async_update_data(self):
        try:
            async with self.session.get('https://api.2dehands.be/sold_items') as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            raise UpdateFailed(f"Failed to fetch data from 2dehands: {e}")