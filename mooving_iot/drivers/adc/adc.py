#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading

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
class AdcImplementationBase:
    def __init__(self):
        _log.debug('AdcImplementationBase instance created.')

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def get_ext_batt_voltage(self) -> float:
        return NotImplementedError

    def get_int_batt_voltage(self) -> float:
        return NotImplementedError

    def ext_batt_is_charging(self) -> bool:
        return NotImplementedError


class Adc:
    def __init__(self, AdcImplCls):
        self._adc_impl: AdcImplementationBase = AdcImplCls()
        _log.debug('Adc instance created.')

    def start(self):
        return self._adc_impl.start()

    def stop(self):
        return self._adc_impl.stop()

    def get_ext_batt_voltage(self) -> float:
        return self._adc_impl.get_ext_batt_voltage()

    def get_int_batt_voltage(self) -> float:
        return self._adc_impl.get_int_batt_voltage()

    def ext_batt_is_charging(self) -> bool:
        return self._adc_impl.ext_batt_is_charging()
