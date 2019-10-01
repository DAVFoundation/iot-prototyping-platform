#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global packages imports
import os
import jwt
import datetime
import time
import paho.mqtt.client as mqttc
import threading
import json
import queue

# Local packages imports
import mooving_iot.utils.logger as logger
import mooving_iot.project_config as prj_cfg
import mooving_iot.libraries.cloud.cloud as cloud


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Public class
#***************************************************************************************************
class GoogleCloudIot(cloud.CloudImplementationBase):
    _JWT_TOKEN_LIFE = 60
    _RECONNECT_MIN_DELAY = 2
    _RECONNECT_MAX_DELAY = 60

    def __init__(self, cloud_conn_params):
        super().__init__(cloud_conn_params)

        self._client_id = ('projects/{}/locations/{}/registries/{}/devices/{}'
            .format(
                self._cloud_conn_params.project_id,
                self._cloud_conn_params.cloud_region,
                self._cloud_conn_params.registry_id,
                self._cloud_conn_params.device_id))

        mqtt_topics_base = '/devices/{}'.format(self._cloud_conn_params.device_id)
        self._mqtt_events_topic = '{base}/events'.format(base=mqtt_topics_base)
        self._mqtt_cmds_topic = '{base}/commands/#'.format(base=mqtt_topics_base)
        self._mqtt_config_topic = '{base}/config'.format(base=mqtt_topics_base)

        self._cmds_queue = queue.Queue(100)
        self._config_queue = queue.Queue(100)

        self._jwt_expire_time_sec = (GoogleCloudIot._JWT_TOKEN_LIFE - 1) * 60
        self._jwt_expire_timer = None

        self._mqtt_client = mqttc.Client(client_id=self._client_id)

        self._mqtt_client.tls_set()

        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.on_publish = self._on_publish
        self._mqtt_client.on_message = self._on_message

        self._mqtt_client.reconnect_delay_set(
            GoogleCloudIot._RECONNECT_MIN_DELAY,
            GoogleCloudIot._RECONNECT_MAX_DELAY)

        _log.info('Google Cloud Client ID: {}'.format(self._client_id))
        _log.info('MQTT events topic: {}'.format(self._mqtt_events_topic))
        _log.info('MQTT commands topic: {}'.format(self._mqtt_cmds_topic))
        _log.info('MQTT configuration topic: {}'.format(self._mqtt_config_topic))
        _log.debug('GoogleCloudIot instance created.')

    def create_connection(self, start_loop=True) -> int:
        self._mqtt_client.username_pw_set(
            username='unused',
            password=self._create_jwt())

        is_failure = True
        while is_failure:
            try:
                conn_status = self._mqtt_client.connect(
                    self._cloud_conn_params.mqtt_url,
                    self._cloud_conn_params.mqtt_port)

                is_failure = False
            except:
                _log.info('Failed to connect.')
                time.sleep(5)

        if start_loop:
            self._mqtt_client.loop_start()
        _log.info('Connect to cloud, status: {}'.format(mqttc.error_string(conn_status)))

        self._jwt_expire_timer = threading.Timer(self._jwt_expire_time_sec, self._jwt_expired)
        self._jwt_expire_timer.start()

        return conn_status

    def send_event(self, payload) -> int:
        json_payload = json.dumps(payload, indent=4)
        msg_info = self._mqtt_client.publish(self._mqtt_events_topic, json_payload, qos=0)

        _log.debug('Send event ID: {}, status: {}'.format(
            msg_info.mid, mqttc.error_string(msg_info.rc)))

        return msg_info.rc

    def wait_for_command(self) -> str:
        return self._cmds_queue.get(True, None)

    def wait_for_configuration(self) -> str:
        return self._config_queue.get(True, None)

    def _jwt_expired(self):
        _log.debug('GoogleCloudIot _jwt_expired called.')
        disconn_status = self._mqtt_client.disconnect()

    def _create_jwt(self):
        current_time_utc = datetime.datetime.utcnow()
        token = {
            'iat': current_time_utc,
            'exp': current_time_utc + datetime.timedelta(minutes=GoogleCloudIot._JWT_TOKEN_LIFE),
            'aud': self._cloud_conn_params.project_id
        }

        with open(self._cloud_conn_params.private_key_filepath, 'r') as f:
            private_key = f.read()

        return jwt.encode(
            token, private_key, algorithm=self._cloud_conn_params.private_key_algorithm)

    def _on_connect(self, client, userdata, flags, rc):
        _log.debug('on_connect event, status: {}'.format(mqttc.error_string(rc)))

        status = self._mqtt_client.subscribe(self._mqtt_cmds_topic, qos=1)
        _log.info('Subscribe on commands topic, status: {}'.format(mqttc.error_string(status[0])))
        status = self._mqtt_client.subscribe(self._mqtt_config_topic, qos=1)
        _log.info('Subscribe on config topic, status: {}'.format(mqttc.error_string(status[0])))

    def _on_disconnect(self, client, userdata, rc):
        _log.debug('on_disconnect event, status: {}'.format(mqttc.error_string(rc)))
        self.create_connection(False)

    def _on_publish(self, client, userdata, mid):
        _log.debug('_on_publish event, event ID: {}.'.format(mid))

    def _on_message(self, client, userdata, message):
        str_payload = message.payload.decode('utf-8')
        if len(str_payload) > 0:
            _log.debug('_on_message event, topic: {}, message: {}'
                .format(message.topic, str_payload))

            if message.topic == self._mqtt_config_topic:
                self._config_queue.put(str_payload, True, None)
            else:
                self._cmds_queue.put(str_payload, True, None)
        else:
            _log.debug('_on_message event empty')
