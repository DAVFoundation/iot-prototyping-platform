#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global imports
import os
import threading
import time
import smbus2
import enum
import traceback

# Project imports
import mooving_iot.utils.logger as logger
import mooving_iot.utils.exit as utils_exit
import mooving_iot.project_config as prj_cfg

import mooving_iot.drivers.acc.acc as acc


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Private variables
#***************************************************************************************************
class ACC_REG_ID(enum.IntEnum):
    WHO_AM_I = 0x0F
    CTRL1 = 0x20
    CTRL2 = 0x21
    CTRL3 = 0x22
    CTRL4 = 0x23
    CTRL5 = 0x24
    CTRL6 = 0x25
    CTRL7 = 0x26
    STATUS = 0x27
    OUT_X_L = 0x28
    IG_CFG1 = 0x30
    IG_SRC1 = 0x31
    IG_THS_X1 = 0x32
    IG_THS_Y1 = 0x33
    IG_THS_Z1 = 0x34
    IG_DUR1 = 0x35
    IG_CFG2 = 0x36
    XL_REFERENCE = 0x3A
    XH_REFERENCE = 0x3B
    YL_REFERENCE = 0x3C
    YH_REFERENCE = 0x3D
    ZL_REFERENCE = 0x3E
    ZH_REFERENCE = 0x3F


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class AccLis2hh12(acc.AccImplementationBase):
    def __init__(self, i2c_instance_num, i2c_addr):
        self._i2c_instance_num = i2c_instance_num
        self._i2c_addr = i2c_addr
        self._acc_data_threshold_update_required = False
        self._acc_data_threshold = 2000
        self._acc_data_threshold_duration = 0x7F * 100

        self._is_acc_out_of_threshold = False

        self._data_lock = threading.Lock()
        self._data_event = threading.Event()
        self._last_data = acc.AccData(0, 0, 0)

        self._start_event = threading.Event()
        self._process_thread = threading.Thread(target=self._process_thread_func)
        self._process_thread.start()

        utils_exit.register_on_exit(self.stop)

        _log.debug('AccLis2hh12 instance created.')

    def start(self):
        # force reboot
        self._write_register(ACC_REG_ID.CTRL6, 0x80)
        # wait until force reboot done
        ctrl3_c_value = 0x80
        while (ctrl3_c_value & 0x80):
            ctrl3_c_value = self._read_register(ACC_REG_ID.CTRL6)

        # check that accelerometer returns correct response
        who_am_i_value = self._read_register(ACC_REG_ID.WHO_AM_I)
        _log.info('Read acc WHO_AM_I value: 0x{:02X}.'.format(who_am_i_value))
        # X, Y, Z, enabled, ODR = 10 Hz, BDU enabled
        self._write_register(ACC_REG_ID.CTRL1, 0x1F)
        #  high-pass filter enable
        self._write_register(ACC_REG_ID.CTRL2, 0x02)
        # interrupt generator 1 on INT1 pin
        self._write_register(ACC_REG_ID.CTRL3, 0x08)
        # increment during a multiple byte access
        self._write_register(ACC_REG_ID.CTRL4, 0x04)
        # interrupt active-high; Interrupt pins push-pull configuration
        self._write_register(ACC_REG_ID.CTRL5, 0x00)
        # interrupt 1 latched
        self._write_register(ACC_REG_ID.CTRL7, 0x04)
        # set threshold
        threshold = int((self._acc_data_threshold * 255) / 2000)
        self._write_register(ACC_REG_ID.IG_THS_X1, threshold)
        self._write_register(ACC_REG_ID.IG_THS_Y1, threshold)
        self._write_register(ACC_REG_ID.IG_THS_Z1, threshold)
        # set duration (for 10 Hz - 100 ms on each sample)
        duration = int(self._acc_data_threshold_duration / 100)
        self._write_register(ACC_REG_ID.IG_DUR1, duration & 0x7F)
        # dummy read to force HP filter output
        self._read_register(ACC_REG_ID.XL_REFERENCE)
        self._read_register(ACC_REG_ID.YL_REFERENCE)
        self._read_register(ACC_REG_ID.ZL_REFERENCE)
        # enable ZHIE, XHIE and YHIE interrupt generation
        self._write_register(ACC_REG_ID.IG_CFG1, 0x2A)
        # read to clear unexpected interrupt
        ig_src1_value = self._read_register(ACC_REG_ID.IG_SRC1)

        self._start_event.set()

    def stop(self):
        self._start_event.clear()
        self._data_event.clear()
        # TODO: deinit acc

    def get_last_data(self) -> acc.AccData:
        with self._data_lock:
            return self._last_data

    def get_data_updated_event(self) -> threading.Event:
        return self._data_event

    def is_acc_out_of_threshold(self) -> bool:
        return self._is_acc_out_of_threshold

    def set_acc_threshold(self, threshold_mg, threshold_duration_ms):
        self._acc_data_threshold = threshold_mg
        self._acc_data_threshold_duration = threshold_duration_ms
        with self._data_lock:
            self._acc_data_threshold_update_required = True

    def _process_thread_func(self):
        try:
            _log.debug('acc process_thread_func thread started.')

            while True:
                self._start_event.wait()

                acc_status = self._read_register(ACC_REG_ID.STATUS)
                # if new data available - read it
                if acc_status & 0x08:
                    # read data from acc
                    last_data = self._read_acc_data()
                    # read if data was out of threshold
                    ig_src1_value = self._read_register(ACC_REG_ID.IG_SRC1)
                    is_acc_out_of_threshold = (ig_src1_value & 0x2A) > 0
                    if self._acc_data_threshold_update_required:
                        # update acc threshold
                        threshold = int((self._acc_data_threshold * 256) / 2000)
                        self._write_register(ACC_REG_ID.IG_THS_X1, threshold)
                        self._write_register(ACC_REG_ID.IG_THS_Y1, threshold)
                        self._write_register(ACC_REG_ID.IG_THS_Z1, threshold)
                        # set duration (for 10 Hz - 100 ms on each sample)
                        duration = int(self._acc_data_threshold_duration / 100)
                        self._write_register(ACC_REG_ID.IG_DUR1, duration & 0x7F)
                        # read to clear unexpected interrupt
                        ig_src1_value = self._read_register(ACC_REG_ID.IG_SRC1)

                    with self._data_lock:
                        self._acc_data_threshold_update_required = False
                        self._last_data = last_data
                        self._is_acc_out_of_threshold = is_acc_out_of_threshold
                        self._data_event.set()

                    time.sleep(0.1)
        except:
            _log.error(traceback.format_exc())
            utils_exit.exit(1)

    def _read_register(self, register_id) -> int:
        write = smbus2.i2c_msg.write(self._i2c_addr, [register_id])
        read = smbus2.i2c_msg.read(self._i2c_addr, 1)
        with smbus2.SMBusWrapper(self._i2c_instance_num) as bus:
            bus.i2c_rdwr(write, read)
        return list(read)[0]

    def _write_register(self, register_id, value):
        with smbus2.SMBusWrapper(self._i2c_instance_num) as bus:
            write = smbus2.i2c_msg.write(self._i2c_addr, [register_id, value])
            bus.i2c_rdwr(write)

    def _read_acc_data(self) -> acc.AccData:
        write = smbus2.i2c_msg.write(self._i2c_addr, [ACC_REG_ID.OUT_X_L])
        read = smbus2.i2c_msg.read(self._i2c_addr, 6)
        with smbus2.SMBusWrapper(self._i2c_instance_num) as bus:
            bus.i2c_rdwr(write, read)

        raw_data = list(read)
        return acc.AccData(
            self._raw_data_to_mg(raw_data[0] | (raw_data[1] << 8)),
            self._raw_data_to_mg(raw_data[2] | (raw_data[3] << 8)),
            self._raw_data_to_mg(raw_data[4] | (raw_data[5] << 8)))

    def _raw_data_to_mg(self, data_reg) -> int:
        if (data_reg & 0x8000) > 0:
            data_reg |= (~0xFFFF)
        return int((data_reg * 2000) / 2**15)
