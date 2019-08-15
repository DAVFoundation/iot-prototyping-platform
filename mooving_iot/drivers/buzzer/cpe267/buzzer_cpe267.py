#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
import time
import traceback
import pigpio
import queue
from typing import Union

# Project imports
import mooving_iot.utils.logger as logger
import mooving_iot.utils.exit as utils_exit
import mooving_iot.project_config as prj_cfg

import mooving_iot.drivers.buzzer.buzzer as buzzer


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class BuzzerCpe267(buzzer.BuzzerImplementationBase):
    def __init__(self, pwm_pin):
        self._pwm_pin = pwm_pin

        self._pigpio : Union[pigpio.pi, None] = None

        self._start_event = threading.Event()
        self._events_queue = queue.Queue(100)
        self._process_thread = threading.Thread(target=self._process_thread_func)
        self._process_thread.start()

        utils_exit.register_on_exit(self.stop)

        _log.debug('BuzzerDrv instance created.')

    def start(self):
        self._pigpio = pigpio.pi()
        self._pigpio.hardware_PWM(self._pwm_pin, 2500, 0)

        self._start_event.set()

    def stop(self):
        self._start_event.clear()

        self._pigpio.stop()

    def set_event(self, event : buzzer.BuzzerEvent):
        self._events_queue.put(event, True, None)

    def clear_all_events(self):
        try:
            while True:
                self._events_queue.get_nowait()
        except:
            self._pigpio.hardware_PWM(self._pwm_pin, 2500, 0)

    def _process_thread_func(self):
        try:
            _log.debug('buzzer _process_tone_func thread started.')

            while True:
                self._start_event.wait()

                event : buzzer.BuzzerEvent = self._events_queue.get(True, None)

                self._pigpio.hardware_PWM(self._pwm_pin,
                    event.frequency,
                    int(event.duty_cycle * 10000))

                time.sleep(event.time)
                self._pigpio.hardware_PWM(self._pwm_pin, 2500, 0)
        except:
            _log.error(traceback.format_exc())
            utils_exit.exit(1)
