#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global packages imports
import datetime
import os
import threading

# Local packages imports
import mooving_iot.project_config as prj_cfg


#***************************************************************************************************
# Private variables
#***************************************************************************************************
_i2c_lock = threading.Lock()


#***************************************************************************************************
# Public functions
#***************************************************************************************************
def i2c_get_lock() -> threading.Lock:
    return _i2c_lock
