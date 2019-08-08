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
import mooving_iot.project_config as prj_cfg

import mooving_iot.libraries.cloud.cloud as lib_cloud
import mooving_iot.libraries.cloud.google_cloud_iot.google_cloud_iot as lib_google_cloud_iot
import mooving_iot.libraries.cloud.cloud_protocol as lib_cloud_protocol

import mooving_iot.libraries.acc_threshold_detector.acc_threshold_detector as lib_acc_thr_detector

import mooving_iot.libraries.device_config.device_config as lib_device_config

import mooving_iot.drivers.acc.acc as drv_acc
import mooving_iot.drivers.acc.lis2hh12.acc_lis2hh12 as drv_acc_lis2hh12


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Private variables
#***************************************************************************************************
# Drivers instances
_acc: Union[drv_acc.Acc, None] = None

# Libraries instances
_device_config = lib_device_config.DeviceConfig.get_instance()
_acc_thr_detector : Union[lib_acc_thr_detector.AccThresholdDetector, None] = None

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
                elif cmd_dict['command'] == 'lock':
                    with _last_telemetry_packet_lock:
                        _last_telemetry_event = lib_cloud_protocol.StateEvent('lock')
                elif cmd_dict['command'] == 'unlock':
                    with _last_telemetry_packet_lock:
                        _last_telemetry_event = lib_cloud_protocol.StateEvent('unlock')
                elif cmd_dict['command'] == 'unavailable':
                    with _last_telemetry_packet_lock:
                        _last_telemetry_event = lib_cloud_protocol.StateEvent('unavailable')
                elif cmd_dict['command'] == 'beep':
                    pass
                elif cmd_dict['command'] == 'alarm':
                    pass

                _telemetry_send_event.set()
    except:
        _log.error(traceback.format_exc())
        logger.Logger.close_log_file()
        os._exit(1)


def _configuration_processing_thread():
    try:
        _log.debug('configuration_processing_thread started.')

        while True:
            cfg_json = _cloud.wait_for_configuration()
            _log.debug('Configuration json: {}'.format(cfg_json))

            _telemetry_send_event.set()
    except:
        _log.error(traceback.format_exc())
        logger.Logger.close_log_file()
        os._exit(1)


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
        logger.Logger.close_log_file()
        os._exit(1)


def _hw_init():
    # Accelerometer driver initialization.
    global _acc
    AccImplClass = drv_acc_lis2hh12.AccLis2hh12
    _acc = drv_acc.Acc(AccImplClass, 0x1D)
    _acc.start()


def _lib_init():
    global _acc_thr_detector
    _acc_thr_detector = lib_acc_thr_detector.AccThresholdDetector(_acc)
    _acc_thr_detector.set_acc_threshold(250, 100, 2000, 5)
    _acc_thr_detector.set_angles_threshold(50, 2000)


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

    _device_config.set_param(lib_device_config.ConfigParam("deviceId", conn_params.device_id))

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
    while True:
        state = "lock"
        device_id = _device_config.get_param("deviceId").value

        if state == "lock":
            wait_time_max = _device_config.get_param("telemetryIntervalLock").value
        elif state == "unlock":
            wait_time_max = _device_config.get_param("telemetryIntervalUnlock").value
        else:
            wait_time_max = _device_config.get_param("telemetryIntervalUnavailable").value

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
