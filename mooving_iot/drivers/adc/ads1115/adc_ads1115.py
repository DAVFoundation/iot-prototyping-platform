#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
import time
import traceback
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Project imports
import mooving_iot.utils.logger as logger
import mooving_iot.utils.i2c_lock as i2c_lock
import mooving_iot.project_config as prj_cfg
import mooving_iot.utils.exit as utils_exit

import mooving_iot.drivers.adc.adc as adc


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Private variables
#***************************************************************************************************
_EXT_BATTERY_DIVIDER_R1 = 1000000
_EXT_BATTERY_DIVIDER_R2 = 18000
_EXT_CHARGER_DIVIDER_R1 = 1000000
_EXT_CHARGER_DIVIDER_R2 = 18000
_VOLTAGE_LEVEL_FILTER_COEF = 0.2

_i2c_lock_obj = i2c_lock.i2c_get_lock()


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class AdcAds1115(adc.AdcImplementationBase):
    __EXT_BATTERY_CHANNEL_ID = 0
    __INT_BATTERY_CHANNEL_ID = 3
    __EXT_BATTERY_CHARGER_CHANNEL_ID = 1
    __EXT_BATTERY_DIVIDER_COEF = (
        (_EXT_BATTERY_DIVIDER_R1 + _EXT_BATTERY_DIVIDER_R2) / _EXT_BATTERY_DIVIDER_R2)
    __EXT_CHARGER_DIVIDER_COEF = (
        (_EXT_CHARGER_DIVIDER_R1 + _EXT_CHARGER_DIVIDER_R2) / _EXT_CHARGER_DIVIDER_R2)
    __EXT_BATTERY_CHARGING_LEVEL = 20.0
    def __init__(self):
        self._i2c = None
        self._ads1115 = None

        self._adc_channels = [
            None,
            None,
            None,
            None
        ]

        self._data_lock = threading.Lock()
        self._channels_voltage = [0, 0, 0, 0]

        self._start_event = threading.Event()
        self._process_thread = threading.Thread(target=self._process_thread_func)
        self._process_thread.start()

        _log.debug('Adc_ADS1115 instance created.')

    def start(self):
        for i in range(4):
            self._channels_voltage[i] = 0

        with _i2c_lock_obj:
            self._i2c = busio.I2C(board.SCL, board.SDA)
            self._ads1115 = ADS.ADS1115(self._i2c)
            self._ads1115.gain = 2/3
            self._adc_channels = [
                AnalogIn(self._ads1115, ADS.P0),
                AnalogIn(self._ads1115, ADS.P1),
                AnalogIn(self._ads1115, ADS.P2),
                AnalogIn(self._ads1115, ADS.P3)
            ]

        self._start_event.set()

    def stop(self):
        self._start_event.clear()

        with _i2c_lock_obj:
            self._i2c.deinit()

        for i in range(4):
            self._channels_voltage[i] = 0

    def get_ext_batt_voltage(self) -> float:
        with self._data_lock:
            return (
                self._channels_voltage[AdcAds1115.__EXT_BATTERY_CHANNEL_ID]
                * AdcAds1115.__EXT_BATTERY_DIVIDER_COEF)

    def get_int_batt_voltage(self) -> float:
        with self._data_lock:
            return self._channels_voltage[AdcAds1115.__INT_BATTERY_CHANNEL_ID]

    def ext_batt_is_charging(self) -> bool:
        with self._data_lock:
            return (
                self._channels_voltage[AdcAds1115.__EXT_BATTERY_CHARGER_CHANNEL_ID]
                * AdcAds1115.__EXT_CHARGER_DIVIDER_COEF
                >= AdcAds1115.__EXT_BATTERY_CHARGING_LEVEL)

    def _process_thread_func(self):
        try:
            _log.debug('adc process_thread_func thread started.')
            while True:
                self._start_event.wait()

                with _i2c_lock_obj:
                    with self._data_lock:
                        for i in range(4):
                            if self._channels_voltage[i] == 0:
                                self._channels_voltage[i] = self._adc_channels[i].voltage
                            else:
                                self._channels_voltage[i] = (
                                    (1.0 - _VOLTAGE_LEVEL_FILTER_COEF) * self._channels_voltage[i]
                                    + _VOLTAGE_LEVEL_FILTER_COEF * self._adc_channels[i].voltage)
                time.sleep(0.1)
        except:
            _log.error(traceback.format_exc())
            utils_exit.exit(1)
