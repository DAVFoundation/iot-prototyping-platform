#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global packages imports
import enum
import os


#***************************************************************************************************
# Constants
#***************************************************************************************************
# Logging level constants
class LogLevel(enum.IntEnum):
    NONE = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    DEBUG = 4


#***************************************************************************************************
# Configuration
#***************************************************************************************************
# Debug mode ON flag
DEBUG = False

# Global logging level
GLOBAL_LOG_LEVEL = LogLevel.DEBUG if DEBUG else LogLevel.INFO
# Enable logging in file
FILE_LOG_ENABLE = False
# Log file path and name
FILE_LOG_PATH = '{current_dir}/../logs'.format(current_dir=os.path.dirname(__file__))
