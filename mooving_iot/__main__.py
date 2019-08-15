#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global packages imports
import os
import traceback
import atexit

# Local packages imports
import mooving_iot.utils.logger as logger
import mooving_iot.utils.exit as utils_exit
import mooving_iot.project_config as prj_cfg

import mooving_iot.application as app


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# main
#***************************************************************************************************
def main():
    try:
        _log.debug('main started.')
        atexit.register(utils_exit.on_exit)

        app.init()
        app.start()

        _log.error('Application exited unexpectedly.')
        utils_exit.exit(1)
    except:
        _log.error(traceback.format_exc())
        utils_exit.exit(1)


#***************************************************************************************************
# Startup point
#***************************************************************************************************
if __name__ == '__main__':
    main()
