#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global packages imports
import board as adafruit_pinout


#***************************************************************************************************
# Hardware configuration
#***************************************************************************************************
# Accelerometer configuration.
class ACC:
    I2C_INST_NUM = 1
    I2C_ADDR = 0x1D

class RELAY:
    SET_PIN = 23
    RESET_PIN = 24

class BUZZER:
    PWM_PIN = 18

class LED_RGB:
    R_PIN = adafruit_pinout.D10
    G_PIN = adafruit_pinout.D10
    B_PIN = adafruit_pinout.D10
