#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
import math
import time

# Project imports
import mooving_iot.utils.logger as logger
import mooving_iot.project_config as prj_cfg

import mooving_iot.drivers.acc.acc as drv_acc


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.INFO)


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class AccAngles:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return 'X: {0:.2f}, Y: {0:.2f}, Z: {0:.2f}.'.format(self.x, self.y, self.z)


class AccThresholdDetector:
    DEFAULT_ACC_ANGLE_X = 0
    DEFAULT_ACC_ANGLE_Y = 0
    DEFAULT_ACC_ANGLE_Z = 90
    def __init__(self, acc_driver : drv_acc.Acc):
        self._acc_driver = acc_driver
        self._last_acc_data = drv_acc.AccData(0, 0, 0)
        self._acc_angles = AccAngles(0, 0, 0)

        self._acc_out_of_thr_peak_count = 0
        self._acc_out_of_thr_start_time_ms = 0
        self._is_acc_out_of_thr = False

        self._angle_out_of_thr_start_time_ms = None
        self._angle_out_of_thr_stop_time_ms = None

        self._acc_total_duration_ms = None
        self._acc_peak_count = None

        self._angle_threshold_degree = None
        self._angle_total_duration_ms = None

    def set_acc_threshold(self, threshold_mg, peak_duration_ms, total_duration_ms, peak_count):
        self._acc_driver.set_acc_threshold(threshold_mg, peak_duration_ms)
        self._acc_total_duration_ms = total_duration_ms
        self._acc_peak_count = peak_count

    def set_angles_threshold(self, threshold_degree, total_duration_ms):
        self._angle_threshold_degree = threshold_degree
        self._angle_total_duration_ms = total_duration_ms

    def get_angles(self) -> AccAngles:
        return self._acc_angles

    def is_acc_out_of_threshold(self) -> bool:
        if self._acc_peak_count != None:
            current_time_ms = int(time.time() * 1000)
            end_time_ms = self._acc_out_of_thr_start_time_ms + self._acc_total_duration_ms

            if current_time_ms > end_time_ms:
                self._is_acc_out_of_thr = self._acc_out_of_thr_peak_count >= self._acc_peak_count
                self._acc_out_of_thr_start_time_ms = current_time_ms
                self._acc_out_of_thr_peak_count = 0

            return self._is_acc_out_of_thr
        else:
            return False

    def is_angles_out_of_threshold(self) -> bool:
        if ((self._angle_out_of_thr_start_time_ms == None) or
            (self._angle_total_duration_ms == None)):
            return False
        else:
            current_time_ms = int(time.time() * 1000)
            return ((self._angle_out_of_thr_start_time_ms + self._angle_total_duration_ms)
                <= current_time_ms)

    def update(self):
        acc_data_updated = self._acc_driver.get_data_updated_event()

        if acc_data_updated.isSet():
            acc_data_updated.clear()
            self._last_acc_data = self._acc_driver.get_last_data()
            is_acc_data_threshold = self._acc_driver.is_acc_out_of_threshold()
            current_time_ms = int(time.time() * 1000)

            _log.debug(
                'Acc data updated: x = {x} mg, y = {y} mg, z = {z} mg. Out of threshold: {thr}.'
                .format(
                    x=self._last_acc_data.x_mg,
                    y=self._last_acc_data.y_mg,
                    z=self._last_acc_data.z_mg,
                    thr=is_acc_data_threshold))

            self._calculate_angles()

            _log.debug(
                'Acc angles updated: x = {x}, y = {y}, z = {z}.'
                .format(
                    x=self._acc_angles.x,
                    y=self._acc_angles.y,
                    z=self._acc_angles.z))

            if self._calc_is_angles_out_of_thr():
                self._angle_out_of_thr_stop_time_ms = None
                if self._angle_out_of_thr_start_time_ms == None:
                    self._angle_out_of_thr_start_time_ms = current_time_ms
            else:
                if self._angle_out_of_thr_stop_time_ms == None:
                    self._angle_out_of_thr_stop_time_ms = current_time_ms
                elif ((self._angle_out_of_thr_stop_time_ms + self._angle_total_duration_ms)
                    <= current_time_ms):
                    self._angle_out_of_thr_start_time_ms = None

            if (self._acc_peak_count != None) and is_acc_data_threshold:
                self._acc_out_of_thr_peak_count += 1

    def _calculate_angles(self):
        x_pow2 = self._last_acc_data.x_mg ** 2
        y_pow2 = self._last_acc_data.y_mg ** 2
        z_pow2 = self._last_acc_data.z_mg ** 2

        g_vector_length = math.sqrt(x_pow2 + y_pow2 + z_pow2)

        x_angle = math.degrees(math.asin(self._last_acc_data.x_mg / g_vector_length))
        y_angle = math.degrees(math.asin(self._last_acc_data.y_mg / g_vector_length))
        z_angle = math.degrees(math.asin(self._last_acc_data.z_mg / g_vector_length))

        self._acc_angles = AccAngles(x_angle, y_angle, z_angle)

    def _calc_is_angles_out_of_thr(self):
        if (self._angle_threshold_degree == None):
            _log.debug('return false')
            return False

        if (
            ((AccThresholdDetector.DEFAULT_ACC_ANGLE_X - self._angle_threshold_degree)
            <= self._acc_angles.x <=
            (AccThresholdDetector.DEFAULT_ACC_ANGLE_X + self._angle_threshold_degree))
            and
            ((AccThresholdDetector.DEFAULT_ACC_ANGLE_Y - self._angle_threshold_degree)
            <= self._acc_angles.y <=
            (AccThresholdDetector.DEFAULT_ACC_ANGLE_Y + self._angle_threshold_degree))
            and
            ((AccThresholdDetector.DEFAULT_ACC_ANGLE_Z - self._angle_threshold_degree)
            <= self._acc_angles.z <=
            (AccThresholdDetector.DEFAULT_ACC_ANGLE_Z + self._angle_threshold_degree))
        ):
            return False
        else:
            return True
