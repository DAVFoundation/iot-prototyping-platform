#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global packages imports
import os
import traceback

# Local packages imports
import mooving_iot.utils.logger as logger
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

        app.init()
        app.start()

        _log.error('Application exited unexpectedly.')
        logger.Logger.close_log_file()
        os._exit(1)
    except:
        _log.error(traceback.format_exc())
        logger.Logger.close_log_file()
        os._exit(1)


#***************************************************************************************************
# Startup point
#***************************************************************************************************
if __name__ == '__main__':
    main()
