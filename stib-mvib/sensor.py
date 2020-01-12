#########################################################################################
# Stib Sensor
#########################################################################################
import datetime
import time
import requests
import logging
import json

from homeassistant.helpers.entity import Entity
from homeassistant.const import STATE_OK


_LOGGER = logging.getLogger(__name__)


ATTR_UPCOMING = 'Upcoming departure'
ATTR_UPCOMING_DESTINATION = 'Upcoming Destination'
ATTR_LINE_ID = 'line'
ATTR_ATTRIBUTION = 'Data provided by opendata-api.stib-mvib.be'


ICON = 'mdi:bus'
CONF_STOPS = 'stops'
CONF_STOP_ID = 'stop_id'
CONF_DIRECTION = 'direction'
CONF_API_TOKEN = 'api_token'
DEFAULT_NAME = 'STIB'


def setup_platform(hass, config, add_entities, discovery_info=None):
    sensors = []
    stops_list = config.get(CONF_STOPS)
    for stop in stops_list:
        sensors.append(StibSensor(stop[CONF_STOP_ID], stop[CONF_DIRECTION], config.get(CONF_API_TOKEN)))

    add_entities(sensors, True)


class StibSensor(Entity):
    """A sensor contains information about a specific traject on a specific stib line"""
    def __init__(self, stopId, direction, api_token):
        self._direction = direction
        self._state = STATE_OK
        self._upcoming = 0
        self._upcoming_destination = direction
        self._stop_id = stopId
        self._line_id = 0
        self._data = StibData(api_token, stopId, direction)
        self._data.update()

    @property
    def name(self):
        return "STIB info for stop with id " + str(self._stop_id)

    @property
    def state(self):
        return self._state

    @property
    def device_state_attributes(self):
        if self._data is not None:
            return {
                    ATTR_UPCOMING: self._upcoming,
                    ATTR_UPCOMING_DESTINATION: self._upcoming_destination,
                    ATTR_LINE_ID: self._line_id,
                    }

    @property
    def icon(self):
        return ICON


    def update(self):
        self._data.update()
        self._line_id = self._data.nextLine
        self._upcoming_destination = self._data.nextDestination
        self._upcoming = self._data.nextDepartureETA


_RESOURCE_BASE = "https://opendata-api.stib-mivb.be"
_OPERATIONMONITORING = "/OperationMonitoring/4.0"
_PASSINGTIMEBYPOINT = "/PassingTimeByPoint"
_ACTUALIZATION_DELTA = 20000


class StibData(object):
    def __init__(self, api_token, stopID, destination = None):
        self.stop = stopID
        self.nextLine = ""
        self.nextDestination = ""
        self.nextDepartureETA = 0
        self.stop_data = {}
        self._api_token = api_token
        self._destination = destination
        self._last_update_time = 0
        self._last_update_data = []

    def update(self):
        if abs(time.time() - self._last_update_time) < _ACTUALIZATION_DELTA:
            _LOGGER.info("Last update was at " + str(self._last_update_time) +
                         " returning cached data. (time is: " + str(time.time()) + ")")
        else:
            _LOGGER.info("Last update was at " + str(self._last_update_time) +
                         " fetching fresh data. (time is: " + str(time.time()) + ")")
            headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer {0}'.format(self._api_token)}

            response = requests.get(_RESOURCE_BASE +
                                    _OPERATIONMONITORING +
                                    _PASSINGTIMEBYPOINT +
                                    self.getPointURL(), headers=headers)
            result = []
            if response.status_code == 200:
                content = json.loads(response.content.decode("utf-8"))
                _LOGGER.info("Got RAW data from STIB " + str(content) + " parsing it now...")
                self.nextDepartureETA = 100000  # set it to a high number then take the minimum
                for passingTime in content["points"][0]["passingTimes"]:
                    if self._destination in (passingTime["destination"]["fr"] + passingTime["destination"]["nl"]):
                        passingTimeETA = datetime.datetime.strptime(passingTime["expectedArrivalTime"], "%Y-%m-%dT%H:%M:%S").timestamp() - time.time()
                        if passingTimeETA < self.nextDepartureETA:
                            self.nextDepartureETA = passingTimeETA
                            self.nextDestination = passingTime["destination"]["fr"] + "-" + passingTime["destination"]["nl"]
                            self.nextLine = passingTime["lineId"]
                        result.append(passingTime)
                self._last_update_time = time.time()
                self._last_update_data = result
            else:
                _LOGGER.error("Impossible to get data from STIB api. Response code: %s. Check %s", response.status_code, response.url)

        return self._last_update_data

    def getPointURL(self):
        return "/"+str(self.stop)

