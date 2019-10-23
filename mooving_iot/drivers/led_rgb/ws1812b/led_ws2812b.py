#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
import time
import traceback
from typing import Union
import queue
import RPi.GPIO as GPIO
import neopixel

# Project imports
import mooving_iot.utils.logger as logger
import mooving_iot.utils.exit as utils_exit
import mooving_iot.project_config as prj_cfg

import mooving_iot.drivers.led_rgb.led_rgb as drv_led_rgb


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class LedWs2812b(drv_led_rgb.LedRgbImplementationBase):
    def __init__(self, r_pin, g_pin, b_pin):
        self._data_pin = r_pin

        self._neopixel : Union[neopixel.NeoPixel, None] = None

        self._events_queue = queue.Queue(100)
        self._start_event = threading.Event()
        self._process_thread = threading.Thread(target=self._process_thread_func)
        self._process_thread.start()

        utils_exit.register_on_exit(self.stop)

        _log.debug('LedDrv instance created.')

    def start(self):
        self._neopixel = neopixel.NeoPixel(self._data_pin, 1)

        self._start_event.set()

    def stop(self):
        self._start_event.clear()

        self._neopixel.fill( (0, 0, 0) )
        self._neopixel.show()
        self._neopixel.deinit()

    def set_event(self, event : drv_led_rgb.LedRgbEvent):
        self._events_queue.put(event, True, None)

    def clear_all_events(self):
        try:
            while True:
                self._events_queue.get_nowait()
        except:
            self._neopixel.fill( (0, 0, 0) )
            self._neopixel.show()

    def _process_thread_func(self):
        try:
            _log.debug('led _process_tone_func thread started.')

            while True:
                self._start_event.wait()

                event : drv_led_rgb.LedRgbEvent = self._events_queue.get(True, None)

                self._neopixel.fill(
                    (int(event.r_bright * 2.55),
                    int(event.g_bright * 2.55),
                    int(event.b_bright * 2.55)) )
                self._neopixel.show()

                time.sleep(event.time)
                self._neopixel.fill( (0, 0, 0) )
                self._neopixel.show()
        except:
            _log.error(traceback.format_exc())
            utils_exit.exit(1)
