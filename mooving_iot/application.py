#***************************************************************************************************
# Run only one instance of script.
#***************************************************************************************************
from tendo import singleton
_me = singleton.SingleInstance()


#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global packages imports
import os
import time
import datetime
import argparse
import threading
import json
from typing import Union
import traceback

# Local packages imports
import mooving_iot.utils.logger as logger
import mooving_iot.utils.exit as utils_exit
import mooving_iot.project_config as prj_cfg
import mooving_iot.hw_config as hw_cfg

import mooving_iot.drivers.acc.acc as drv_acc
import mooving_iot.drivers.acc.lis2hh12.acc_lis2hh12 as drv_acc_lis2hh12
import mooving_iot.drivers.relay.relay as drv_relay
import mooving_iot.drivers.relay.adjh23005.relay_adjh23005 as drv_relay_adjh23005
import mooving_iot.drivers.buzzer.buzzer as drv_buzzer
import mooving_iot.drivers.buzzer.cpe267.buzzer_cpe267 as drv_buzzer_cpe267
import mooving_iot.drivers.led_rgb.led_rgb as drv_led_rgb
import mooving_iot.drivers.led_rgb.ws1812b.led_ws2812b as drv_led_ws2812b

import mooving_iot.libraries.cloud.cloud as lib_cloud
import mooving_iot.libraries.cloud.google_cloud_iot.google_cloud_iot as lib_google_cloud_iot
import mooving_iot.libraries.cloud.cloud_protocol as lib_cloud_protocol
import mooving_iot.libraries.acc_threshold_detector.acc_threshold_detector as lib_acc_thr_detector
import mooving_iot.libraries.device_config.device_config as lib_device_config
import mooving_iot.libraries.buzzer_pattern.buzzer_pattern as lib_buzzer_pattern
import mooving_iot.libraries.led_rgb_pattern.led_rgb_pattern as lib_led_rgb_pattern


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Private variables
#***************************************************************************************************
# Drivers instances
_acc: Union[drv_acc.Acc, None] = None
_relay: Union[drv_relay.Relay, None] = None
_buzzer: Union[drv_buzzer.Buzzer, None] = None
_led_rgb: Union[drv_led_rgb.LedRgb, None] = None

# Libraries instances
_device_config = lib_device_config.DeviceConfig.get_instance()
_acc_thr_detector : Union[lib_acc_thr_detector.AccThresholdDetector, None] = None
_buzzer_pattern_gen : Union[lib_buzzer_pattern.BuzzerPatternGenerator, None] = None
_led_rgb_pattern_gen : Union[lib_led_rgb_pattern.LedRgbPatternGenerator, None] = None

# Module variables
_cloud : Union[lib_cloud.Cloud, None] = None

_telemetry_send_event = threading.Event()

_last_telemetry_packet_lock = threading.Lock()
_last_telemetry_packet : Union[lib_cloud_protocol.TelemetryPacket, None] = None
_last_telemetry_event : lib_cloud_protocol.Event = lib_cloud_protocol.EmptyEvent()


#***************************************************************************************************
# Private functions
#***************************************************************************************************
def _parse_command_line_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '--project_id',
            required=True,
            help='GCP cloud project name')
    parser.add_argument(
            '--registry_id',
            required=True,
            help='Cloud IoT Core registry id')
    parser.add_argument(
            '--device_id',
            required=True,
            help='Cloud IoT Core device id')
    parser.add_argument(
            '--private_key_file',
            default='./keys/ec_private.pem',
            help='Path to private key file.')
    parser.add_argument(
            '--algorithm',
            choices=('RS256', 'ES256'),
            default='ES256',
            help='Which encryption algorithm to use to generate the JWT.')
    parser.add_argument(
            '--cloud_region', required=True, help='GCP cloud region')
    parser.add_argument(
            '--mqtt_bridge_hostname',
            default='mqtt.googleapis.com',
            help='MQTT bridge hostname.')
    parser.add_argument(
            '--mqtt_bridge_port',
            choices=(8883, 443),
            default=8883,
            type=int,
            help='MQTT bridge port.')
    return parser.parse_args()


def _command_processing_thread():
    try:
        _log.debug('command_processing_thread started.')

        while True:
            cmd_json = _cloud.wait_for_command()
            _log.debug('Command json: {}'.format(cmd_json))

            cmd_packet = lib_cloud_protocol.CommandPacket(cmd_json)
            cmd_dict = cmd_packet.get_dict()

            global _last_telemetry_event

            if cmd_packet.is_valid():
                if cmd_dict['command'] == 'set-intervals':
                    if 'lock' in cmd_dict['states']:
                        param = lib_device_config.ConfigParam(
                            'telemetryIntervalLock', cmd_dict['states']['lock'])
                        _device_config.set_param(param)
                    if 'unlock' in cmd_dict['states']:
                        param = lib_device_config.ConfigParam(
                            'telemetryIntervalUnlock', cmd_dict['states']['unlock'])
                        _device_config.set_param(param)
                    if 'unavailable' in cmd_dict['states']:
                        param = lib_device_config.ConfigParam(
                            'telemetryIntervalUnavailable', cmd_dict['states']['unavailable'])
                        _device_config.set_param(param)
                elif ((cmd_dict['command'] == 'lock')
                    or (cmd_dict['command'] == 'unlock')
                    or (cmd_dict['command'] == 'unavailable')):
                    with _last_telemetry_packet_lock:
                        param = lib_device_config.ConfigParam('deviceState', cmd_dict['command'])
                        _device_config.set_param(param)
                        _last_telemetry_event = lib_cloud_protocol.StateEvent(cmd_dict['command'])
                elif cmd_dict['command'] == 'beep':
                    _buzzer_pattern_gen.start_pattern(lib_buzzer_pattern.BUZZER_PATTERN_ID.BEEP,
                        cmd_dict['volume'])
                elif cmd_dict['command'] == 'alarm':
                    _buzzer_pattern_gen.start_pattern(lib_buzzer_pattern.BUZZER_PATTERN_ID.ALARM,
                        cmd_dict['volume'])

                _telemetry_send_event.set()
    except:
        _log.error(traceback.format_exc())
        utils_exit.exit(1)


def _configuration_processing_thread():
    try:
        _log.debug('configuration_processing_thread started.')

        while True:
            cfg_json = _cloud.wait_for_configuration()
            _log.debug('Configuration json: {}'.format(cfg_json))

            _telemetry_send_event.set()
    except:
        _log.error(traceback.format_exc())
        utils_exit.exit(1)


def _threshold_detection_thread():
    try:
        _log.debug('threshold_detection_thread started.')

        acc_data_updated = _acc.get_data_updated_event()
        is_acc_out_of_thr = False
        is_angle_out_of_thr = False

        while True:
            # Accelerometer threshold detection
            _acc_thr_detector.update()
            is_acc_out_of_thr_new = _acc_thr_detector.is_acc_out_of_threshold()
            is_angle_out_of_thr_new = _acc_thr_detector.is_angles_out_of_threshold()

            if is_acc_out_of_thr_new != is_acc_out_of_thr:
                _log.debug('Acc data out of threshold updated: {}'.format(is_acc_out_of_thr_new))
                is_acc_out_of_thr = is_acc_out_of_thr_new

            if is_angle_out_of_thr_new != is_angle_out_of_thr:
                _log.debug('Angle out of threshold updated: {}'.format(is_angle_out_of_thr_new))
                is_angle_out_of_thr = is_angle_out_of_thr_new

            time.sleep(0.02)
    except:
        _log.error(traceback.format_exc())
        utils_exit.exit(1)


def _hw_init():
    global _acc
    AccImplClass = drv_acc_lis2hh12.AccLis2hh12
    _acc = drv_acc.Acc(AccImplClass, hw_cfg.ACC.I2C_INST_NUM, hw_cfg.ACC.I2C_ADDR)
    _acc.start()

    global _relay
    RelayImplClass = drv_relay_adjh23005.RelayAdjh23005
    _relay = drv_relay.Relay(RelayImplClass, hw_cfg.RELAY.SET_PIN, hw_cfg.RELAY.RESET_PIN)
    _relay.start(_device_config.get_param('deviceState').value == 'unlock')

    global _buzzer
    BuzzerImplClass = drv_buzzer_cpe267.BuzzerCpe267
    _buzzer = drv_buzzer.Buzzer(BuzzerImplClass, hw_cfg.BUZZER.PWM_PIN)
    _buzzer.start()

    global _led_rgb
    LedRgbImplClass = drv_led_ws2812b.LedWs2812b
    _led_rgb = drv_led_rgb.LedRgb(LedRgbImplClass,
        hw_cfg.LED_RGB.R_PIN, hw_cfg.LED_RGB.G_PIN, hw_cfg.LED_RGB.B_PIN)
    _led_rgb.start()


def _lib_init():
    global _acc_thr_detector
    _acc_thr_detector = lib_acc_thr_detector.AccThresholdDetector(_acc)
    _acc_thr_detector.set_acc_threshold(
        _device_config.get_param('accThresholdMg').value,
        _device_config.get_param('accPeakDurationMs').value,
        _device_config.get_param('accTotalDurationMs').value,
        _device_config.get_param('accPeakCount').value)
    _acc_thr_detector.set_angles_threshold(
        _device_config.get_param('accAngleThresholdDegree').value,
        _device_config.get_param('accAngleTotalDurationMs').value)

    global _buzzer_pattern_gen
    _buzzer_pattern_gen = lib_buzzer_pattern.BuzzerPatternGenerator(_buzzer)

    global _led_rgb_pattern_gen
    _led_rgb_pattern_gen = lib_led_rgb_pattern.LedRgbPatternGenerator(_led_rgb)


#***************************************************************************************************
# Public functions
#***************************************************************************************************
# Application initialization
def init():

    _hw_init()
    _lib_init()

    args = _parse_command_line_args()

    conn_params = lib_cloud.CloudConnectionParameters(
        project_id=args.project_id,
        cloud_region=args.cloud_region,
        registry_id=args.registry_id,
        device_id=args.device_id,
        private_key_filepath=args.private_key_file,
        private_key_algorithm=args.algorithm,
        mqtt_url=args.mqtt_bridge_hostname,
        mqtt_port=args.mqtt_bridge_port)

    _device_config.set_param(lib_device_config.ConfigParam('deviceId', conn_params.device_id))

    global _cloud
    _cloud = lib_cloud.Cloud(lib_google_cloud_iot.GoogleCloudIot, conn_params)

    _cloud.create_connection()

    cmd_thread = threading.Thread(target=_command_processing_thread)
    cmd_thread.start()
    cfg_thread = threading.Thread(target=_configuration_processing_thread)
    cfg_thread.start()
    thr_thread = threading.Thread(target=_threshold_detection_thread)
    thr_thread.start()

    _log.debug('Application init completed.')


# Application loop
def start():
    previous_state = None

    while True:
        state = _device_config.get_param('deviceState').value
        device_id = _device_config.get_param('deviceId').value

        if state == 'lock':
            wait_time_max = _device_config.get_param('telemetryIntervalLock').value
            if previous_state != state:
                _relay.set_state(False)
                _led_rgb_pattern_gen.start_pattern(lib_led_rgb_pattern.LED_RGB_PATTERN_ID.LOCKED)
        elif state == 'unlock':
            wait_time_max = _device_config.get_param('telemetryIntervalUnlock').value
            if previous_state != state:
                _relay.set_state(True)
                _led_rgb_pattern_gen.start_pattern(lib_led_rgb_pattern.LED_RGB_PATTERN_ID.UNLOCKED)
        else:
            wait_time_max = _device_config.get_param('telemetryIntervalUnavailable').value
            if previous_state != state:
                _relay.set_state(False)
                _led_rgb_pattern_gen.stop_pattern()

        previous_state = state

        global _last_telemetry_packet
        global _last_telemetry_event

        with _last_telemetry_packet_lock:
            _last_telemetry_packet = lib_cloud_protocol.TelemetryPacket(
                device_id=device_id,
                interval=wait_time_max,
                ext_batt=100,
                int_batt=100,
                longtitude=0,
                latitude=0,
                alarm=False,
                state=state,
                event=_last_telemetry_event)

            _last_telemetry_event = lib_cloud_protocol.EmptyEvent()

            _log.debug('Sending packet: {}'.format(str(_last_telemetry_packet)))
            _cloud.send_event(_last_telemetry_packet.to_map())

        _log.debug('Wait to next telemetry send event: {} sec'.format(wait_time_max))

        _telemetry_send_event.wait(wait_time_max)
        _telemetry_send_event.clear()
