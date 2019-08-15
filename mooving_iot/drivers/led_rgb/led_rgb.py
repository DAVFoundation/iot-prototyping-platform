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
class LedRgbEvent:
    # Brightness in percentages [0, 100]
    def __init__(self, r_bright, g_bright, b_bright, time):
        self.r_bright = r_bright
        self.g_bright = g_bright
        self.b_bright = b_bright
        self.time = time


class LedRgbImplementationBase:
    def __init__(self, r_pin, g_pin, b_pin):
        _log.debug('LedImplementationBase instance created.')

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def set_event(self, event : LedRgbEvent):
        raise NotImplementedError

    def clear_all_events(self):
        raise NotImplementedError


class LedRgb:
    def __init__(self, LedRgbImplCls, r_pin, g_pin, b_pin):
        self._led_rgb_impl: LedImplementationBase = LedRgbImplCls(r_pin, g_pin, b_pin)
        _log.debug('Led instance created.')

    def start(self):
        return self._led_rgb_impl.start()

    def stop(self):
        return self._led_rgb_impl.stop()

    def set_event(self, event : LedRgbEvent):
        return self._led_rgb_impl.set_event(event)

    def clear_all_events(self):
        return self._led_rgb_impl.clear_all_events()
