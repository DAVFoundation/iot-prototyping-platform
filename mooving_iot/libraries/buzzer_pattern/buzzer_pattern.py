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

import mooving_iot.drivers.buzzer.buzzer as drv_buzzer


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Private variables
#***************************************************************************************************
_alarm_pattern = [
    drv_buzzer.BuzzerEvent(100, 1),
    drv_buzzer.BuzzerEvent(0, 0.2)]

_beep_pattern = [
    drv_buzzer.BuzzerEvent(100, 1),
    drv_buzzer.BuzzerEvent(0, 1),
    drv_buzzer.BuzzerEvent(100, 1, 3200),
    drv_buzzer.BuzzerEvent(0, 1)]


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class BUZZER_PATTERN_ID(enum.IntEnum):
    BEEP = 0
    ALARM = 1


class BuzzerPatternGenerator:
    _PATTERNS_TABLE = {
        BUZZER_PATTERN_ID.ALARM: _alarm_pattern,
        BUZZER_PATTERN_ID.BEEP: _beep_pattern
    }

    def __init__(self, buzzer_driver : drv_buzzer.Buzzer):
        self._buzzer_driver = buzzer_driver
        self._pattern_repeate_count = None
        self._current_pattern = None
        self._current_pattern_volume = 0

        self._pattern_thread : Union[threading.Thread, None] = None
        self._pattern_thread_stop = False

    def start_pattern(self, pattern_id, volume, repeate_count=None):
        self.stop_pattern()

        if volume == 0:
            return

        self._current_pattern_volume = volume
        self._pattern_repeate_count = repeate_count
        self._current_pattern = BuzzerPatternGenerator._PATTERNS_TABLE.get(pattern_id, None)
        if self._current_pattern == None:
            return

        _log.debug('Start buzzer pattern with ID: {}.'.format(pattern_id))

        self._pattern_thread = threading.Thread(target=self._event_send_thread)
        self._pattern_thread_stop = False
        self._pattern_thread.start()

    def stop_pattern(self):
        _log.debug('Stop buzzer pattern.')

        self._pattern_thread_stop = True
        self._buzzer_driver.clear_all_events()
        if (self._pattern_thread != None) and self._pattern_thread.is_alive():
            self._pattern_thread.join()

    def _event_send_thread(self):
        try:
            while True:
                for event in self._current_pattern:
                    duty_cycle_volume = 0
                    if event.duty_cycle > 0:
                        duty_cycle_volume = self._current_pattern_volume / 2.0
                    event_copy = drv_buzzer.BuzzerEvent(duty_cycle_volume, event.time, event.frequency)
                    self._buzzer_driver.set_event(event_copy)

                if self._pattern_repeate_count != None:
                    self._pattern_repeate_count -= 1
                    if self._pattern_repeate_count < 0:
                        return
                if self._pattern_thread_stop:
                    return
        except:
            _log.error(traceback.format_exc())
            utils_exit.exit(1)
