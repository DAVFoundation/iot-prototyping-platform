#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
import time
import traceback
import serial
import pynmea2
import math
import RPi.GPIO as GPIO

# Project imports
import mooving_iot.utils.logger as logger
import mooving_iot.project_config as prj_cfg
import mooving_iot.drivers.GNSS.GNSS as gnss


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class GNSS_Teseo_liv3f(gnss.GNSSImplementationBase):
    _SERIAL_PORT = "/dev/ttyS0"
    _DEFAULT_GPS_CHANGE_TRES = 0.05
    def __init__(self, reset_pin):
        self._reset_pin = reset_pin
        self._longitude = "0.0"
        self._latitude = "0.0"
        self._altitude = "0.0"
        self._heading = "0.0"
        self._valid = False

        self._serial = None

        self._data_lock = threading.Lock()
        self._last_data = gnss.GNSSData("0.0", "0.0", "0.0", "0.0", False)
        self._coord = None
        self._gps_speed = "0"

        self._start_event = threading.Event()
        self._process_thread = threading.Thread(
            target=self._process_thread_func)
        self._process_thread.start()
        _log.debug('GNSS_Teseo_liv3f instance created.')

    def start(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._reset_pin, GPIO.OUT)
        GPIO.output(self._reset_pin, GPIO.HIGH)

        self._serial = serial.Serial(GNSS_Teseo_liv3f._SERIAL_PORT, baudrate=9600, timeout=0.5)
        self._hard_reset()
        self._send_UART_data("$PSTMRESTOREPAR*11")
        self._send_UART_data("$PSTMSRR*49")
        time.sleep(1)
        self._start_event.set()

    def stop(self):
        self._start_event.clear()
        GPIO.cleanup(self._reset_pin)

    def get_last_data(self) -> gnss.GNSSData:
        with self._data_lock:
            return self._last_data

    def get_valid(self):
        with self._data_lock:
            return self._valid

    def get_coord(self):
        with self._data_lock:
            return self._coord

    def get_longitude(self):
        with self._data_lock:
            return self._longitude

    def get_latitude(self):
        with self._data_lock:
            return self._latitude

    def get_altitude(self):
        with self._data_lock:
            return self._altitude

    def get_heading(self):
        with self._data_lock:
            return self._heading

    def get_gps_data_change(self, gps_longitude, gps_latitude):
        with self._data_lock:
            is_latitude_changed = (
                (abs(float(self._latitude) - float(gps_latitude)) * 110.574)
                > GNSS_Teseo_liv3f._DEFAULT_GPS_CHANGE_TRES)
            is_longitude_changed = (
                (abs(float(self._longitude) - float(gps_longitude)) *
                111.320 * math.cos(math.radians(float(self._latitude) - float(gps_latitude))))
                > GNSS_Teseo_liv3f._DEFAULT_GPS_CHANGE_TRES)
            if is_latitude_changed or is_longitude_changed:
                return [ True , self._longitude , self._latitude ]
            else:
                return [ False , self._longitude , self._latitude ]

    def _process_thread_func(self):
        try:
            _log.debug('gnss process_thread_func thread started.')
            coord = "0.0"
            longitude = "0.0"
            latitude = "0.0"
            valid = False
            altitude = "0.0"
            heading = "0.0"
            gps_speed = "0"
            while True:
                self._start_event.wait()
                _data = self._serial.readline()
                try:
                    if ((_data[:1].decode('utf-8') == '$')
                        and (_data.decode('utf-8').find("PSTM") == -1)):
                        _data = _data[:-2]
                        msg = pynmea2.parse(_data.decode('utf-8'))
                        try:
                            if msg.sentence_type == "GGA":
                                lat_P = msg.lat.split(".")
                                lon_P = msg.lon.split(".")

                                # Convert from DDM to DD format
                                if msg.lat_dir == 'S':
                                    latitude = str(
                                        (-1) * round(float(lat_P[0][:-2])
                                        + (float(lat_P[0][-2:] + "." + lat_P[1]) / 60), 6))
                                else:
                                    latitude = str(
                                        round(float(lat_P[0][:-2])
                                        + (float(lat_P[0][-2:] + "." + lat_P[1]) / 60), 6))

                                if msg.lon_dir == 'W':										
                                    longitude = str(
                                        (-1) * round(float(lon_P[0][:-2])
                                        + (float(lon_P[0][-2:] + "." + lon_P[1]) / 60), 6))
                                else:
                                    longitude = str(
                                        round(float(lon_P[0][:-2])
                                        + (float(lon_P[0][-2:] + "." + lon_P[1]) / 60), 6))								

                                coord = (lat_P[0][:-2] + " " + lat_P[0][-2:] + "." + lat_P[1]
                                    + ", " + lon_P[0][:-2] + " " + lon_P[0][-2:] + "." + lon_P[1])
                                altitude = str(msg.altitude)

                                if msg.gps_qual == 0 or str(msg.gps_qual) == "None":
                                    valid = False
                                else:
                                    valid = True
                        except:
                            _log.debug('GNSS_Teseo_liv3f GGA parse error')
                        try:
                            if msg.sentence_type == "VTG":
                                heading = str(msg.true_track)
                                gps_speed = str(msg.spd_over_grnd_kmph)
                        except:
                            _log.debug('GNSS_Teseo_liv3f VTG parse error')
                        try:
                            with self._data_lock:
                                self._coord = coord
                                self._longitude = longitude
                                self._latitude = latitude
                                self._valid = valid
                                self._altitude = altitude
                                self._heading = heading
                                self._gps_speed = gps_speed
                                _last_data = gnss.GNSSData(
                                    longitude, latitude, altitude, heading, valid)
                        except:
                            _log.debug('GNSS_Teseo_liv3f data lock error')
                        time.sleep(0.5)

                except:
                    _log.debug('GNSS_Teseo_liv3f can not parse data.')
        except:
            GPIO.cleanup()
            _log.error(traceback.format_exc())
            logger.Logger.close_log_file()
            os._exit(1)

    def _send_UART_data(self, data):
        self._serial.write(str.encode(data))
        self._serial.write(str.encode("\r\n"))

    def _hard_reset(self):
        self._serial.readline()
        GPIO.output(self._reset_pin, GPIO.LOW)
        time.sleep(0.5)
        GPIO.output(self._reset_pin, GPIO.HIGH)
        time.sleep(2)
