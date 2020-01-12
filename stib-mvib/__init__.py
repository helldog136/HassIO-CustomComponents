"""This is the STIB (Brussels public transportation) integration"""

DOMAIN = 'stib_service'


def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""
    hass.data[DOMAIN] = {
        'transportation_times': []
    }

    hass.helpers.discovery.load_platform('sensor', DOMAIN, {}, config)

    # Return boolean to indicate that initialization was successfully.
    return True