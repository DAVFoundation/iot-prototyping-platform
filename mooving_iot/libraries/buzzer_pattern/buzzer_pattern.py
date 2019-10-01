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
_BUZZER_HIGH_TONE_FREQ = 3300
_BUZZER_LOW_TONE_FREQ = 2300

_DUTY_CYCLE_OFF = 0

if prj_cfg.DEBUG:
    _DUTY_CYCLE_LOW = 5
    _DUTY_CYCLE_MEDIUM = 10
    _DUTY_CYCLE_HIGH = 15
else:
    _DUTY_CYCLE_LOW = 15
    _DUTY_CYCLE_MEDIUM = 30
    _DUTY_CYCLE_HIGH = 50

_alarm_pattern = [
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_HIGH, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2)]

_beep_pattern = [
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_MEDIUM, 0.3, _BUZZER_LOW_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_MEDIUM, 0.3, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_MEDIUM, 0.3, _BUZZER_LOW_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 1)]

_lock_pattern = [
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_LOW, 0.3, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_LOW, 0.3, _BUZZER_LOW_TONE_FREQ)]

_unlock_pattern = [
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_LOW, 0.3, _BUZZER_LOW_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_LOW, 0.3, _BUZZER_HIGH_TONE_FREQ)]

_alarm_pattern_phase_1 = [
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_LOW, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_LOW, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2)]

_alarm_pattern_phase_2 = [
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_MEDIUM, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_MEDIUM, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_MEDIUM, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_MEDIUM, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_MEDIUM, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2)]

_alarm_pattern_phase_3 = [
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_HIGH, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_HIGH, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_HIGH, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_HIGH, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 0.2),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_HIGH, 0.8, _BUZZER_HIGH_TONE_FREQ),
    drv_buzzer.BuzzerEvent(_DUTY_CYCLE_OFF, 5.2)]


#***************************************************************************************************
# Public variables
#***************************************************************************************************
VOLUME_OFF = _DUTY_CYCLE_OFF * 2
VOLUME_LOW = _DUTY_CYCLE_LOW * 2
VOLUME_MEDIUM = _DUTY_CYCLE_MEDIUM * 2
VOLUME_HIGH = _DUTY_CYCLE_HIGH * 2

PATTERN_REPEAT_FOREVER = 0xFFFFFFFF


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class BUZZER_PATTERN_ID(enum.IntEnum):
    BEEP = 0
    ALARM = 1
    LOCKED = 2
    UNLOCKED = 3
    ALARM_PHASE_1 = 4
    ALARM_PHASE_2 = 5
    ALARM_PHASE_3 = 6


class BuzzerPatternGenerator:
    _PATTERNS_TABLE = {
        BUZZER_PATTERN_ID.ALARM: _alarm_pattern,
        BUZZER_PATTERN_ID.BEEP: _beep_pattern,
        BUZZER_PATTERN_ID.LOCKED: _lock_pattern,
        BUZZER_PATTERN_ID.UNLOCKED: _unlock_pattern,
        BUZZER_PATTERN_ID.ALARM_PHASE_1: _alarm_pattern_phase_1,
        BUZZER_PATTERN_ID.ALARM_PHASE_2: _alarm_pattern_phase_2,
        BUZZER_PATTERN_ID.ALARM_PHASE_3: _alarm_pattern_phase_3
    }

    def __init__(self, buzzer_driver : drv_buzzer.Buzzer):
        self._buzzer_driver = buzzer_driver
        self._pattern_repeate_count = 0
        self._current_pattern = None
        self._current_pattern_volume = 0

        self._pattern_thread : Union[threading.Thread, None] = None
        self._pattern_thread_stop = False

    def start_pattern(self, pattern_id, volume=None, repeate_count=0):
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
                    duty_cycle = _DUTY_CYCLE_OFF
                    if event.duty_cycle != _DUTY_CYCLE_OFF:
                        if self._current_pattern_volume != None:
                            duty_cycle = self._current_pattern_volume / 2.0
                        else:
                            duty_cycle = event.duty_cycle
                    event_copy = drv_buzzer.BuzzerEvent(duty_cycle, event.time, event.frequency)
                    self._buzzer_driver.set_event(event_copy)

                self._pattern_repeate_count -= 1
                if self._pattern_repeate_count < 0:
                    return
                if self._pattern_thread_stop:
                    return
        except:
            _log.error(traceback.format_exc())
            utils_exit.exit(1)
