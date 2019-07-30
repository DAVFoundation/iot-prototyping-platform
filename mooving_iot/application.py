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

# Local packages imports
import mooving_iot.utils.logger as logger
import mooving_iot.project_config as prj_cfg

import mooving_iot.libraries.cloud.cloud as lib_cloud
import mooving_iot.libraries.cloud.google_cloud_iot.google_cloud_iot as lib_google_cloud_iot


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Private variables
#***************************************************************************************************
# Drivers instances

# Libraries instances
_cloud: Union[lib_cloud.Cloud, None] = None

# Module variables
_telemetry_send_event = threading.Event()

_last_telemetry_packet_lock = threading.Lock()
_last_telemetry_packet = None



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
    while True:
        cmd_json = _cloud.wait_for_command()
        _log.debug('Command json: {}'.format(cmd_json))

        _telemetry_send_event.set()


def _configuration_processing_thread():
    while True:
        cfg_json = _cloud.wait_for_configuration()
        _log.debug('Configuration json: {}'.format(cfg_json))

        _telemetry_send_event.set()


def _threshold_detection_thread():
    _log.debug('threshold_detection_thread started.')

    while True:
        time.sleep(0.02)


def _hw_init():
    pass


#***************************************************************************************************
# Public functions
#***************************************************************************************************
# Application initialization
def init():

    _hw_init()

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
        with _last_telemetry_packet_lock:
            _last_telemetry_packet = {
                'timestamp': datetime.datetime.now().isoformat()
            }

            _log.debug('Sending packet: {}'.format(str(_last_telemetry_packet)))
            _cloud.send_event(_last_telemetry_packet)

        wait_time_max = 10
        _log.debug('Wait to next telemetry send event: {} sec'.format(wait_time_max))

        _telemetry_send_event.wait(wait_time_max)
        _telemetry_send_event.clear()
