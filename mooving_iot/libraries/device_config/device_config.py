#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
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
class ConfigParam:
    def __init__(self, name: str, value):
        self.name = name
        self.value = value


class ConfigParamDescription:
    def __init__(self, param: ConfigParam, writable=True, max_value=None, min_value=None):
        self._param = param
        self._writable = writable
        self._max_value = max_value
        self._min_value = min_value

    def set_param_value(self, value):
        if (self._max_value != None) and (self._min_value != None) and self._writable:
            if (value >= self._min_value) and (value <= self._max_value):
                self._param.value = value
                _log.debug('Set param: {}, value: {}'.format(self._param.name, value))
        elif self._writable:
            self._param.value = value
            _log.debug('Set param: {}, value: {}'.format(self._param.name, value))

    def get_param(self) -> ConfigParam:
        return self._param


# Singleton class
class DeviceConfig:
    __instance = None
    __instance_lock = threading.Lock()

    @staticmethod
    def get_instance() -> 'DeviceConfig':
        with DeviceConfig.__instance_lock:
            if DeviceConfig.__instance == None:
                DeviceConfig(DeviceConfig.__instance_lock)
            return DeviceConfig.__instance

    def __init__(self, instance_lock=None):
        if instance_lock is DeviceConfig.__instance_lock:
            self._params_desc = [
                ConfigParamDescription(
                    ConfigParam(name='telemetryIntervalUnlock', value=15),
                    writable=True, max_value=1000, min_value=1),
                ConfigParamDescription(
                    ConfigParam(name='telemetryIntervalLock', value=60),
                    writable=True, max_value=1000, min_value=1),
                ConfigParamDescription(
                    ConfigParam(name='telemetryIntervalUnavailable', value=60),
                    writable=True, max_value=1000, min_value=1),
                ConfigParamDescription(
                    ConfigParam(name='deviceId', value="device_id"),
                    writable=True)
            ]

            DeviceConfig.__instance = self
        else:
            raise PermissionError(
                'This is a Singleton class, use get_instance() method instead of constructor!')

    def set_param(self, param: ConfigParam):
        for param_desc in self._params_desc:
            if param_desc.get_param().name == param.name:
                param_desc.set_param_value(param.value)

    def get_param(self, param_name: str) -> Union[ConfigParam, None]:
        for param_desc in self._params_desc:
            if param_desc.get_param().name == param_name:
                return param_desc.get_param()

        return None
