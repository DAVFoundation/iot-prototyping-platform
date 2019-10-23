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
_on_exit_callbacks = []


#***************************************************************************************************
# Public functions
#***************************************************************************************************
def on_exit():
    for callback in _on_exit_callbacks:
        callback()


def exit(n):
    on_exit()
    os._exit(n)


def register_on_exit(callback):
    _on_exit_callbacks.append(callback)
