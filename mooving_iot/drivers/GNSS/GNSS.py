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
class GNSSData:
    def __init__(self, longitude, latitude, altitude, heading, valid):
        self._longitude = longitude
        self._latitude = latitude
        self._altitude = altitude
        self._heading = heading
        self._valid = valid

class GNSSImplementationBase:
    def __init__(self, _reset_pin):
        _log.debug('GNSSImplementationBase instance created.')

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def get_last_data(self) -> GNSSData:
        return NotImplementedError
    def get_coord(self):
        return NotImplementedError
    def get_longitude(self):
        return NotImplementedError
    def get_latitude(self):
        return NotImplementedError
    def get_valid(self):
        return NotImplementedError
    def get_altitude(self):
        return NotImplementedError
    def get_heading(self):
        return NotImplementedError
    def get_gps_data_change(self, gps_longitude, gps_latitude):
        return NotImplementedError


class GNSS:
    def __init__(self, GNSSImplCls, _reset_pin):
        self._gnss_impl: GNSSImplementationBase = GNSSImplCls(_reset_pin)
        _log.debug('GNSS instance created.')

    def start(self):
        return self._gnss_impl.start()

    def stop(self):
        return self._gnss_impl.stop()
    
    def get_coord(self):
        return self._gnss_impl.get_coord()

    def get_longitude(self):
        return self._gnss_impl.get_longitude()

    def get_latitude(self):
        return self._gnss_impl.get_latitude()
    
    def get_valid(self):
        return self._gnss_impl.get_valid()
    
    def get_altitude(self):
        return self._gnss_impl.get_altitude()
    
    def get_heading(self):
        return self._gnss_impl.get_heading()

    def get_gps_data_change(self, gps_longitude, gps_latitude):
        return self._gnss_impl.get_gps_data_change(gps_longitude, gps_latitude)
    
    def get_last_data(self) -> GNSSData:
        return self._gnss_impl.get_last_data()
    

