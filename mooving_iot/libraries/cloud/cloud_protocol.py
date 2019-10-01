#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import datetime
import json
from typing import Union

# Project imports
import mooving_iot.utils.logger as logger
import mooving_iot.project_config as prj_cfg


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class Event:
    def __init__(self):
        pass

    def to_map(self) -> dict:
        raise NotImplementedError

    def __str__(self) -> str:
        return str(self.to_map())


class EmptyEvent(Event):
    def __init__(self):
        pass

    def to_map(self) -> dict:
        return {}


class StateEvent(Event):
    def __init__(self, state : str):
        self._state = state

    def to_map(self) -> dict:
        return {
            'type': self._state
        }


class ChargingEvent(Event):
    def __init__(self, is_charging : bool):
        self._is_charging = is_charging

    def to_map(self) -> dict:
        return {
            'charging': 'true' if self._is_charging else 'false'
        }


class AccMovementEvent(Event):
    def __init__(self, is_moving : bool):
        self._is_moving = is_moving

    def to_map(self) -> dict:
        return {
            'accMoving': 'true' if self._is_moving else 'false'
        }


class AccFallEvent(Event):
    def __init__(self, is_fall : bool):
        self._is_fall = is_fall

    def to_map(self) -> dict:
        return {
            'accFall': 'true' if self._is_fall else 'false'
        }


class ExtBattEvent(Event):
    def __init__(self, voltage : float):
        self._voltage = voltage

    def to_map(self) -> dict:
        return {
            'batteryVoltage': round(self._voltage, 3)
        }


class IntBattEvent(Event):
    def __init__(self, voltage : float):
        self._voltage = voltage

    def to_map(self) -> dict:
        return {
            'internalBatteryVoltage': round(self._voltage, 3)
        }


class TelemetryPacket:
    def __init__(self,
        device_id, interval, ext_batt, int_batt, ext_batt_charging,
        longtitude, latitude, alarm, state,
        event : Event=EmptyEvent()):
        self._device_id = device_id
        self._interval = interval
        self._ext_batt = ext_batt
        self._int_batt = int_batt
        self._ext_batt_charging = ext_batt_charging
        self._longtitude = longtitude
        self._latitude = latitude
        self._alarm = alarm
        self._state = state
        self._event = event
        self._timestamp_utc = datetime.datetime.utcnow().isoformat()

    def __str__(self) -> str:
        return str(self.to_map())

    def to_map(self) -> dict:
        return {
            'deviceId': self._device_id,
            'interval': self._interval,
            'timestamp': self._timestamp_utc,
            'batteryVoltage': round(self._ext_batt, 3),
            'internalBatteryVoltage': round(self._int_batt, 3),
            'charging': 'true' if self._ext_batt_charging else 'false',
            'longitude': self._longtitude,
            'latitude': self._latitude,
            'alarm': 'true' if self._alarm else 'false',
            'state': self._state,
            'event': self._event.to_map()
        }


class CommandPacket:
    def __init__(self, cmd_json : str):
        self._is_valid = False
        self._cmd_dict = json.loads(cmd_json)

        if ('command' in self._cmd_dict) and ('vehicleId' in self._cmd_dict):
            if self._cmd_dict['command'] == 'lock':
                self._is_valid = True
            elif self._cmd_dict['command'] == 'unlock':
                self._is_valid = True
            elif self._cmd_dict['command'] == 'unavailable':
                self._is_valid = True
            elif self._cmd_dict['command'] == 'beep':
                if ('volume' in self._cmd_dict) and (0 <= self._cmd_dict['volume'] <= 100):
                    self._is_valid = True
            elif self._cmd_dict['command'] == 'alarm':
                if ('volume' in self._cmd_dict) and (0 <= self._cmd_dict['volume'] <= 100):
                    self._is_valid = True
            elif self._cmd_dict['command'] == 'set-intervals':
                if 'states' in self._cmd_dict:
                    self._is_valid = True

    def is_valid(self) -> bool:
        return self._is_valid

    def get_dict(self) -> Union[dict, None]:
        if self._is_valid:
            return self._cmd_dict

        return None
