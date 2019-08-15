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
class AccData:
    def __init__(self, x, y, z):
        self.x_mg = x
        self.y_mg = y
        self.z_mg = z


class AccImplementationBase:
    def __init__(self, i2c_instance_num, i2c_addr):
        _log.debug('AccImplementationBase instance created.')

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def get_last_data(self) -> AccData:
        raise NotImplementedError

    def get_data_updated_event(self) -> threading.Event:
        raise NotImplementedError

    def is_acc_out_of_threshold(self) -> bool:
        raise NotImplementedError

    def set_acc_threshold(self, threshold_mg, threshold_duration_ms):
        raise NotImplementedError


class Acc:
    def __init__(self, AccImplCls, i2c_instance_num, i2c_addr):
        self._acc_impl: AccImplementationBase = AccImplCls(i2c_instance_num, i2c_addr)

        _log.debug('Acc instance created.')

    def start(self):
        return self._acc_impl.start()

    def stop(self):
        return self._acc_impl.stop()

    def get_last_data(self) -> AccData:
        return self._acc_impl.get_last_data()

    def get_data_updated_event(self) -> threading.Event:
        return self._acc_impl.get_data_updated_event()

    def is_acc_out_of_threshold(self) -> bool:
        return self._acc_impl.is_acc_out_of_threshold()

    def set_acc_threshold(self, threshold_mg, threshold_duration_ms):
        return self._acc_impl.set_acc_threshold(threshold_mg, threshold_duration_ms)
