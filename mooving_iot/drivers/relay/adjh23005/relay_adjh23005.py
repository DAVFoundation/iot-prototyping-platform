#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
import time
import traceback
import queue
import RPi.GPIO as GPIO

# Project imports
import mooving_iot.utils.logger as logger
import mooving_iot.utils.exit as utils_exit
import mooving_iot.project_config as prj_cfg

import mooving_iot.drivers.relay.relay as relay


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class RelayAdjh23005(relay.RelayImplementationBase):
    STATE_CHANGE_TIME = 0.05

    def __init__(self, set_pin, reset_pin):
        self._set_pin = set_pin
        self._reset_pin = reset_pin
        self._current_state = None

        self._state_queue = queue.Queue(100)

        self._start_event = threading.Event()
        self._process_thread = threading.Thread(target=self._process_thread_func)
        self._process_thread.start()

        utils_exit.register_on_exit(self.stop)

        _log.debug('RelayADJH23005 instance created.')

    def start(self, state=False):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._set_pin, GPIO.OUT)
        GPIO.setup(self._reset_pin, GPIO.OUT)
        GPIO.output(self._set_pin, GPIO.LOW)
        GPIO.output(self._reset_pin, GPIO.LOW)

        self._start_event.set()
        self.set_state(state)

    def stop(self):
        self._start_event.clear()
        GPIO.setup(self._set_pin, GPIO.IN)
        GPIO.setup(self._reset_pin, GPIO.IN)

    def set_state(self, state : bool):
        _log.debug('set relay state: {}.'.format(state))
        self._state_queue.put(state, True, None)

    def _process_thread_func(self):
        try:
            _log.debug('relay process_thread_func thread started.')

            while True:
                self._start_event.wait()

                state = self._state_queue.get(True, None)

                if state != self._current_state:
                    pin = self._set_pin if state else self._reset_pin
                    GPIO.output(pin, GPIO.HIGH)
                    time.sleep(RelayAdjh23005.STATE_CHANGE_TIME)
                    GPIO.output(pin, GPIO.LOW)
                    self._current_state = state

                time.sleep(0.1)
        except:
            _log.error(traceback.format_exc())
            utils_exit.exit(1)
