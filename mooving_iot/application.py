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
import mooving_iot.drivers.adc.adc as drv_adc
import mooving_iot.drivers.adc.ads1115.adc_ads1115 as drv_adc_ads1115
import mooving_iot.drivers.GNSS.GNSS as gnss
import mooving_iot.drivers.GNSS.teseo_liv3f.teseo_liv3f as teseo_liv3f

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
_adc: Union[drv_adc.Adc, None] = None
_GNSS: Union[gnss.GNSS, None] = None

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
_last_telemetry_events : list = []

_is_alarm = False


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
                    # clear threshold detection to avoid immediate alarm after unlock state
                    _acc_thr_detector.clear()
                    param = lib_device_config.ConfigParam('deviceState', cmd_dict['command'])
                    _device_config.set_param(param)
                    with _last_telemetry_packet_lock:
                        _last_telemetry_events.append(
                            lib_cloud_protocol.StateEvent(cmd_dict['command']))
                elif cmd_dict['command'] == 'beep':
                    _buzzer_pattern_gen.start_pattern(lib_buzzer_pattern.BUZZER_PATTERN_ID.BEEP,
                        cmd_dict['volume'], lib_buzzer_pattern.PATTERN_REPEAT_FOREVER)
                elif cmd_dict['command'] == 'alarm':
                    _buzzer_pattern_gen.start_pattern(lib_buzzer_pattern.BUZZER_PATTERN_ID.ALARM,
                        cmd_dict['volume'], lib_buzzer_pattern.PATTERN_REPEAT_FOREVER)

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

    except:
        _log.error(traceback.format_exc())
        utils_exit.exit(1)


def _threshold_detection_thread():
    try:
        _log.debug('threshold_detection_thread started.')

        is_acc_out_of_thr = False
        is_angle_out_of_thr = False
        is_gps_data_change_detected = False
        last_longitude = _GNSS.get_longitude()
        last_latitude = _GNSS.get_latitude()
        is_ext_batt_charging = _adc.ext_batt_is_charging()
        ext_batt_voltage = _adc.get_ext_batt_voltage()
        int_batt_voltage = _adc.get_int_batt_voltage()

        alarm_active = False
        alarm_phase = 0
        alarm_start_time_ms = 0

        while True:
            state = _device_config.get_param('deviceState').value

            # Batteries voltages and charging detection
            ext_batt_voltage_new = _adc.get_ext_batt_voltage()
            int_batt_voltage_new = _adc.get_int_batt_voltage()
            is_ext_batt_charging_new = _adc.ext_batt_is_charging()
            int_batt_threshold = _device_config.get_param('intBattThresholdV').value
            ext_batt_threshold = _device_config.get_param('extBattThresholdV').value
            alarm_active = False

            if ((int_batt_voltage_new >= int_batt_voltage + int_batt_threshold)
                or (int_batt_voltage_new <= int_batt_voltage - int_batt_threshold)
            ):
                int_batt_voltage = int_batt_voltage_new
                _log.debug('Internal battery voltage: {} V.'.format(int_batt_voltage))
                with _last_telemetry_packet_lock:
                    _last_telemetry_events.append(
                        lib_cloud_protocol.IntBattEvent(int_batt_voltage))
                _telemetry_send_event.set()

            if ((ext_batt_voltage_new >= ext_batt_voltage + ext_batt_threshold)
                or (ext_batt_voltage_new <= ext_batt_voltage - ext_batt_threshold)
            ):
                ext_batt_voltage = ext_batt_voltage_new
                _log.debug('External battery voltage: {} V.'.format(ext_batt_voltage))
                with _last_telemetry_packet_lock:
                    _last_telemetry_events.append(
                        lib_cloud_protocol.ExtBattEvent(ext_batt_voltage))
                _telemetry_send_event.set()

            if is_ext_batt_charging_new != is_ext_batt_charging:
                is_ext_batt_charging = is_ext_batt_charging_new
                _log.debug('External battery charge: {}.'.format(is_ext_batt_charging))
                with _last_telemetry_packet_lock:
                    _last_telemetry_events.append(
                        lib_cloud_protocol.ChargingEvent(is_ext_batt_charging))
                _telemetry_send_event.set()

            # Accelerometer movement and angles threshold detection
            is_acc_out_of_thr_new = _acc_thr_detector.is_acc_out_of_threshold()
            is_angle_out_of_thr_new = _acc_thr_detector.is_angles_out_of_threshold()


            if (is_acc_out_of_thr_new != is_acc_out_of_thr) and (state != 'unlock'):
                is_acc_out_of_thr = is_acc_out_of_thr_new
                _log.debug('Acc data out of threshold updated: {}'.format(is_acc_out_of_thr))
                with _last_telemetry_packet_lock:
                    _last_telemetry_events.append(
                        lib_cloud_protocol.AccMovementEvent(is_acc_out_of_thr))
                _telemetry_send_event.set()

            if (is_angle_out_of_thr_new != is_angle_out_of_thr) and (state != 'unlock'):
                is_angle_out_of_thr = is_angle_out_of_thr_new
                angles = _acc_thr_detector.get_angles()
                _log.debug('Angles are: x: {}, y: {}, z: {}.'.format(angles.x, angles.y, angles.z))
                _log.debug('Angle out of threshold updated: {}'.format(is_angle_out_of_thr))
                with _last_telemetry_packet_lock:
                    _last_telemetry_events.append(
                        lib_cloud_protocol.AccFallEvent(is_angle_out_of_thr))
                _telemetry_send_event.set()

            # GPS threshold detection
            is_gps_data_change_detected_new, new_longitude, new_latitude = (
                _GNSS.get_gps_data_change(last_longitude, last_latitude))
            if ((is_gps_data_change_detected_new != is_gps_data_change_detected)
                and (state != 'unlock') and (_GNSS.get_valid()==True)):
                if ((new_longitude != "0.0") and (last_longitude != "0.0")
                    and (new_latitude != "0.0") and (last_latitude != "0.0")):
                    is_gps_data_change_detected = is_gps_data_change_detected_new
                last_longitude = new_longitude
                last_latitude = new_latitude
                _log.debug('GPS position has been changed')
                with _last_telemetry_packet_lock:
                    _last_telemetry_events.append(
                        lib_cloud_protocol.GNSSMovementEvent(is_gps_data_change_detected))
                _telemetry_send_event.set()

            alarm_active = (alarm_active or is_gps_data_change_detected or is_acc_out_of_thr
                or is_angle_out_of_thr)

            # Process alarm if required
            global _is_alarm
            if alarm_active and state != "unlock":
                current_time_ms = int(time.time() * 1000)
                if alarm_start_time_ms == 0:
                    _is_alarm = True
                    alarm_start_time_ms = current_time_ms

                first_phase_timeout_ms = (
                    _device_config.get_param('firstPhaseAlarmTimeout').value * 1000)
                second_phase_timeout_ms = (
                    _device_config.get_param('secondPhaseAlarmTimeout').value * 1000)
                third_phase_timeout_ms = (
                    _device_config.get_param('thirdPhaseAlarmTimeout').value * 1000)

                if alarm_start_time_ms + first_phase_timeout_ms >= current_time_ms:
                    if alarm_phase == 0:
                        _log.debug('Alarm first phase started.')
                        _buzzer_pattern_gen.start_pattern(
                            lib_buzzer_pattern.BUZZER_PATTERN_ID.ALARM_PHASE_1)
                        alarm_phase += 1
                        pass
                elif (alarm_start_time_ms + second_phase_timeout_ms <= current_time_ms
                    and alarm_start_time_ms + third_phase_timeout_ms >= current_time_ms
                ):
                    if alarm_phase == 1:
                        _log.debug('Alarm second phase started.')
                        _buzzer_pattern_gen.start_pattern(
                            lib_buzzer_pattern.BUZZER_PATTERN_ID.ALARM_PHASE_2)
                        alarm_phase += 1
                        pass
                else:
                    if alarm_phase == 2:
                        _log.debug('Alarm third phase started.')
                        _buzzer_pattern_gen.start_pattern(
                            lib_buzzer_pattern.BUZZER_PATTERN_ID.ALARM_PHASE_3,
                            None, lib_buzzer_pattern.PATTERN_REPEAT_FOREVER)
                        alarm_phase += 1
                        pass
            elif alarm_phase != 0:
                _is_alarm = False
                _buzzer_pattern_gen.stop_pattern()
                _log.debug('Alarm finished.')
                alarm_phase = 0
                alarm_start_time_ms = 0
                pass

            time.sleep(0.1)
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

    global _GNSS
    GNSSImplClass = teseo_liv3f.GNSS_Teseo_liv3f
    _GNSS = gnss.GNSS(GNSSImplClass, hw_cfg.GPS.RST_PIN)
    _GNSS.start()

    global _adc
    AdcImplClass = drv_adc_ads1115.AdcAds1115
    _adc = drv_adc.Adc(AdcImplClass)
    _adc.start()


def _on_dev_config_changed_acc_cb():
    _log.debug('Update acc params.')

    _acc_thr_detector.set_acc_threshold(
        _device_config.get_param('accThresholdMg').value,
        _device_config.get_param('accPeakDurationMs').value,
        _device_config.get_param('accTotalDurationMs').value,
        _device_config.get_param('accPeakCount').value)
    _acc_thr_detector.set_angles_threshold(
        _device_config.get_param('accAngleThresholdDegree').value,
        _device_config.get_param('accAngleTotalDurationMs').value)


def _lib_init():
    global _acc_thr_detector
    _acc_thr_detector = lib_acc_thr_detector.AccThresholdDetector(_acc)
    _on_dev_config_changed_acc_cb()
    _device_config.set_on_change_callback(_on_dev_config_changed_acc_cb)

    global _buzzer_pattern_gen
    _buzzer_pattern_gen = lib_buzzer_pattern.BuzzerPatternGenerator(_buzzer)

    global _led_rgb_pattern_gen
    _led_rgb_pattern_gen = lib_led_rgb_pattern.LedRgbPatternGenerator(_led_rgb)


def _update_state(state):
    if state == 'lock':
        _relay.set_state(False)
        _led_rgb_pattern_gen.start_pattern(
            lib_led_rgb_pattern.LED_RGB_PATTERN_ID.LOCKED,
            lib_led_rgb_pattern.PATTERN_REPEAT_FOREVER)
        _buzzer_pattern_gen.start_pattern(lib_buzzer_pattern.BUZZER_PATTERN_ID.LOCKED)
    elif state == 'unlock':
        _relay.set_state(True)
        _led_rgb_pattern_gen.start_pattern(
            lib_led_rgb_pattern.LED_RGB_PATTERN_ID.UNLOCKED,
            lib_led_rgb_pattern.PATTERN_REPEAT_FOREVER)
        _buzzer_pattern_gen.start_pattern(lib_buzzer_pattern.BUZZER_PATTERN_ID.UNLOCKED)
    else:
        _relay.set_state(False)
        _led_rgb_pattern_gen.stop_pattern()
        _buzzer_pattern_gen.stop_pattern()


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

    previous_state = _device_config.get_param('deviceState').value
    _update_state(previous_state)

    _cloud.create_connection()

    while True:
        state = _device_config.get_param('deviceState').value
        device_id = _device_config.get_param('deviceId').value

        wait_time_max = 0
        if state == 'lock':
            wait_time_max = _device_config.get_param('telemetryIntervalLock').value
        elif state == 'unlock':
            wait_time_max = _device_config.get_param('telemetryIntervalUnlock').value
        else:
            wait_time_max = _device_config.get_param('telemetryIntervalUnavailable').value

        if previous_state != state:
            previous_state = state
            _update_state(state)

        global _last_telemetry_packet

        with _last_telemetry_packet_lock:
            if len(_last_telemetry_events) == 0:
                _last_telemetry_events.append(lib_cloud_protocol.EmptyEvent())

            _last_telemetry_packet = lib_cloud_protocol.TelemetryPacket(
                device_id=device_id,
                interval=wait_time_max,
                ext_batt=_adc.get_ext_batt_voltage(),
                int_batt=_adc.get_int_batt_voltage(),
                ext_batt_charging=_adc.ext_batt_is_charging(),
                latitude=_GNSS.get_latitude(),
                longtitude=_GNSS.get_longitude(),
                altitude=_GNSS.get_altitude(),
                heading=_GNSS.get_heading(),
                alarm=_is_alarm,
                state=state,
                event=_last_telemetry_events.pop(0))

            if len(_last_telemetry_events) == 0:
                _telemetry_send_event.clear()

            _log.debug('Sending packet: {}'.format(str(_last_telemetry_packet)))
            _cloud.send_event(_last_telemetry_packet.to_map())

        _log.debug('Wait to next telemetry send event: {} sec.'.format(wait_time_max))
        _telemetry_send_event.wait(wait_time_max)
