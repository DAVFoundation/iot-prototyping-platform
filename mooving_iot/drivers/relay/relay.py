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
class RelayImplementationBase:
    def __init__(self, set_pin, reset_pin):
        _log.debug('RelayImplementationBase instance created.')

    def start(self, state=False):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def set_state(self, state : bool):
        raise NotImplementedError


class Relay:
    def __init__(self, RelayImplCls, set_pin, reset_pin):
        self._relay_impl: RelayImplementationBase = RelayImplCls(set_pin, reset_pin)
        _log.debug('Relay instance created.')

    def start(self, state=False):
        return self._relay_impl.start(state)

    def stop(self):
        return self._relay_impl.stop()

    def set_state(self, state : bool):
        return self._relay_impl.set_state(state)
