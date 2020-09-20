"""Test component setup."""
from homeassistant.setup import async_setup_component

DOMAIN = "media_player"


async def test_async_setup(hass):
    """Test the component gets setup."""
    x = await async_setup_component(hass, DOMAIN, {})
    print(x)
    assert x is True
