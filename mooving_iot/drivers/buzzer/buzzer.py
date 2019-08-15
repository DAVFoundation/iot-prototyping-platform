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
class BuzzerEvent:
    def __init__(self, duty_cycle, time, frequency=2800):
        self.frequency = frequency # from 2300 to 3300 Hz
        self.time = time
        self.duty_cycle = duty_cycle


class BuzzerImplementationBase:
    def __init__(self, pwm_pin):
        _log.debug('BuzzerImplementationBase instance created.')

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def set_event(self, event : BuzzerEvent):
        raise NotImplementedError

    def clear_all_events(self):
        raise NotImplementedError


class Buzzer:
    def __init__(self, BuzzerImplCls, pwm_pin):
        self._buzz_impl: BuzzerImplementationBase = BuzzerImplCls(pwm_pin)
        _log.debug('Buzzer instance created.')

    def start(self):
        return self._buzz_impl.start()

    def stop(self):
        return self._buzz_impl.stop()

    def set_event(self, event : BuzzerEvent):
        return self._buzz_impl.set_event(event)

    def clear_all_events(self):
        return self._buzz_impl.clear_all_events()
