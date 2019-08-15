#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global packages imports
import datetime
import os
import threading

# Local packages imports
import mooving_iot.project_config as prj_cfg
import mooving_iot.utils.exit as utils_exit


#***************************************************************************************************
# Private constants
#***************************************************************************************************
_MSG_TYPE_STR_ERR = 'ERROR'
_MSG_TYPE_STR_WARN = 'WARNING'
_MSG_TYPE_STR_INFO = 'INFO'
_MSG_TYPE_STR_DEBUG = 'DEBUG'


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class Logger:
    __log_file = None
    __file_lock = threading.Lock()
    __print_lock = threading.Lock()

    def __init__(self, module_name, log_level):
        assert type(module_name) is str, 'Value should be a string!'
        assert isinstance(log_level, prj_cfg.LogLevel), 'Value should be a LogLevel enum value!'

        self._module_name = module_name
        self._log_level = log_level

        if prj_cfg.FILE_LOG_ENABLE and (Logger.__log_file == None):
            file_path_name = '{path}/log_{date}.log'.format(
                path=prj_cfg.FILE_LOG_PATH,
                date=datetime.datetime.utcnow().strftime('%Y_%m_%d_T%H_%M_%S_%f'))

            with Logger.__file_lock:
                try:
                    os.makedirs(prj_cfg.FILE_LOG_PATH, exist_ok=True)
                    Logger.__log_file = open(file=file_path_name, mode='w')
                except OSError as err:
                    self.error('Cannot open file: {file}, error: {err}'
                        .format(file=file_path_name, err=err))
                else:
                    utils_exit.register_on_exit(Logger.close_log_file)

    def error(self, value, *args):
        if self._is_log_enabled(prj_cfg.LogLevel.ERROR):
            self._print(_MSG_TYPE_STR_ERR, value, *args)

    def warning(self, value, *args):
        if self._is_log_enabled(prj_cfg.LogLevel.WARNING):
            self._print(_MSG_TYPE_STR_WARN, value, *args)

    def info(self, value, *args):
        if self._is_log_enabled(prj_cfg.LogLevel.INFO):
            self._print(_MSG_TYPE_STR_INFO, value, *args)

    def debug(self, value, *args):
        if self._is_log_enabled(prj_cfg.LogLevel.DEBUG):
            self._print(_MSG_TYPE_STR_DEBUG, value, *args)

    @staticmethod
    def close_log_file():
        if Logger.__log_file != None:
            Logger.__log_file.close()

    def _print(self, msg_type, value, *args):
        assert type(msg_type) is str, 'Value should be a string!'
        assert type(value) is str, 'Value should be a string!'

        with Logger.__print_lock:
            format_str = '[{date}] <{type}> "{module}": {value}'.format(
                date=datetime.datetime.utcnow().isoformat(),
                module=self._module_name,
                type=msg_type,
                value=value)

            print(format_str, *args)
            if prj_cfg.FILE_LOG_ENABLE and (Logger.__log_file != None):
                print(format_str, *args, file=Logger.__log_file)

    def _is_log_enabled(self, log_level):
        return (self._log_level >= log_level) and (prj_cfg.GLOBAL_LOG_LEVEL >= log_level)
