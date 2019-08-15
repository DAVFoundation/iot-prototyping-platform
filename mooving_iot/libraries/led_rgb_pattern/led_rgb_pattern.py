#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
import traceback
import math
import time
import enum
from typing import Union

# Project imports
import mooving_iot.project_config as prj_cfg
import mooving_iot.utils.exit as utils_exit
import mooving_iot.utils.logger as logger

import mooving_iot.drivers.led_rgb.led_rgb as drv_led_rgb


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Private variables
#***************************************************************************************************
_unlocked_pattern = [
    drv_led_rgb.LedRgbEvent(0, 100, 0, 0.5),
    drv_led_rgb.LedRgbEvent(0, 0, 0, 0.5)]

_locked_pattern = [
    drv_led_rgb.LedRgbEvent(100, 0, 0, 0.5),
    drv_led_rgb.LedRgbEvent(0, 0, 0, 0.5)]


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class LED_RGB_PATTERN_ID(enum.IntEnum):
    UNLOCKED = 0
    LOCKED = 1


class LedRgbPatternGenerator:
    _PATTERNS_TABLE = {
        LED_RGB_PATTERN_ID.LOCKED: _locked_pattern,
        LED_RGB_PATTERN_ID.UNLOCKED: _unlocked_pattern
    }

    def __init__(self, led_rgb_driver : drv_led_rgb.LedRgb):
        self._led_rgb_driver = led_rgb_driver
        self._pattern_repeate_count = None
        self._current_pattern = None

        self._pattern_thread : Union[threading.Thread, None] = None
        self._pattern_thread_stop = False

    def start_pattern(self, pattern_id, repeate_count=None):
        self.stop_pattern()

        self._pattern_repeate_count = repeate_count
        self._current_pattern = LedRgbPatternGenerator._PATTERNS_TABLE.get(pattern_id, None)
        if self._current_pattern == None:
            return

        _log.debug('Start LED RGB pattern with ID: {}.'.format(pattern_id))

        self._pattern_thread = threading.Thread(target=self._event_send_thread)
        self._pattern_thread_stop = False
        self._pattern_thread.start()

    def stop_pattern(self):
        _log.debug('Stop LED RGB pattern.')

        self._pattern_thread_stop = True
        self._led_rgb_driver.clear_all_events()
        if (self._pattern_thread != None) and self._pattern_thread.is_alive():
            self._pattern_thread.join()

    def _event_send_thread(self):
        try:
            while True:
                for event in self._current_pattern:
                    self._led_rgb_driver.set_event(event)

                if self._pattern_repeate_count != None:
                    self._pattern_repeate_count -= 1
                    if self._pattern_repeate_count < 0:
                        return
                if self._pattern_thread_stop:
                    return
        except:
            _log.error(traceback.format_exc())
            utils_exit.exit(1)
