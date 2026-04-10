# Configuration Flow

from homeassistant import config_entries

class MyIntegrationConfigFlow(config_entries.ConfigFlow, domain="2dehands"):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id='user')
        # Process user input
        return self.async_create_entry(title="My Integration", data=user_input)