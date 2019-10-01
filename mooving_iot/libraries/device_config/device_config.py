#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
from typing import Union
import json

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
    __config_file_path_name = '{path}/device_config.json'.format(path=prj_cfg.FILE_CONFIG_PATH)

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
                    ConfigParam(name='deviceId', value='device_id'),
                    writable=True),
                ConfigParamDescription(
                    ConfigParam(name='deviceState', value='lock'),
                    writable=True),
                ConfigParamDescription(
                    ConfigParam(name='accThresholdMg', value=250),
                    writable=True, max_value=1999, min_value=1),
                ConfigParamDescription(
                    ConfigParam(name='accPeakDurationMs', value=100),
                    writable=True, max_value=10000, min_value=0),
                ConfigParamDescription(
                    ConfigParam(name='accTotalDurationMs', value=2000),
                    writable=True, max_value=100000, min_value=0),
                ConfigParamDescription(
                    ConfigParam(name='accPeakCount', value=5),
                    writable=True, max_value=1000000, min_value=1),
                ConfigParamDescription(
                    ConfigParam(name='accAngleThresholdDegree', value=50),
                    writable=True, max_value=89, min_value=1),
                ConfigParamDescription(
                    ConfigParam(name='accAngleTotalDurationMs', value=2000),
                    writable=True, max_value=1000000, min_value=1),
                ConfigParamDescription(
                    ConfigParam(name='intBattThresholdV', value=0.2),
                    writable=True, max_value=5.0, min_value=0.1),
                ConfigParamDescription(
                    ConfigParam(name='extBattThresholdV', value=2.0),
                    writable=True, max_value=100.0, min_value=0.1),
                ConfigParamDescription(
                    ConfigParam(name='firstPhaseAlarmTimeout', value=2),
                    writable=True, max_value=100, min_value=1),
                ConfigParamDescription(
                    ConfigParam(name='secondPhaseAlarmTimeout', value=5),
                    writable=True, max_value=200, min_value=2),
                ConfigParamDescription(
                    ConfigParam(name='thirdPhaseAlarmTimeout', value=15),
                    writable=True, max_value=300, min_value=3)
            ]

            self._on_change_callbacks = []

            if os.path.isfile(DeviceConfig.__config_file_path_name):
                self._load_params()

            DeviceConfig.__instance = self
        else:
            raise PermissionError(
                'This is a Singleton class, use get_instance() method instead of constructor!')

    def set_param(self, param: ConfigParam):
        for param_desc in self._params_desc:
            if param_desc.get_param().name == param.name:
                param_desc.set_param_value(param.value)

        self._store_params()
        for callback in self._on_change_callbacks:
            callback()

    def get_param(self, param_name: str) -> Union[ConfigParam, None]:
        for param_desc in self._params_desc:
            if param_desc.get_param().name == param_name:
                return param_desc.get_param()

        return None

    def set_on_change_callback(self, callback):
        self._on_change_callbacks.append(callback)

    def _store_params(self):
        params_dict = {}

        for param_desc in self._params_desc:
            param = param_desc.get_param()
            params_dict[param.name] = param.value

        os.makedirs(prj_cfg.FILE_CONFIG_PATH, exist_ok=True)
        with open(file=DeviceConfig.__config_file_path_name, mode='w') as config_file:
            json.dump(obj=params_dict, fp=config_file, indent=4)

    def _load_params(self):
        config_dict = None
        with open(file=DeviceConfig.__config_file_path_name, mode='r') as config_file:
            config_dict = json.load(config_file)

        for param_name in config_dict:
            cfg_param = ConfigParam(param_name, config_dict[param_name])
            self.set_param(cfg_param)
