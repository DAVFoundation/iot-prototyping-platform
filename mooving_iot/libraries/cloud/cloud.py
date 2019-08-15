#***************************************************************************************************
# Imports
#***************************************************************************************************
# Global packages imports
import os
import jwt
import paho.mqtt.client as mqtt

# Local packages imports
import mooving_iot.utils.logger as logger
import mooving_iot.project_config as prj_cfg


#***************************************************************************************************
# Module logger
#***************************************************************************************************
_log = logger.Logger(os.path.basename(__file__)[0:-3], prj_cfg.LogLevel.DEBUG)


#***************************************************************************************************
# Public classes
#***************************************************************************************************
class CloudConnectionParameters:
    def __init__(self,
        project_id, cloud_region, registry_id, device_id,
        private_key_filepath, private_key_algorithm,
        mqtt_url, mqtt_port
    ):
        self.project_id = project_id
        self.cloud_region = cloud_region
        self.registry_id = registry_id
        self.device_id = device_id
        self.private_key_filepath = private_key_filepath
        self.private_key_algorithm = private_key_algorithm
        self.mqtt_url = mqtt_url
        self.mqtt_port = mqtt_port

        _log.debug('CloudConnectionParameters instance created.')

    def __str__(self):
        return (
            '\tProject ID: {}, Cloud region: {}, Registry ID: {}, Device ID: {},\n'
                .format(self.project_id, self.cloud_region, self.registry_id, self.device_id)
            + '\tPrivate key: {}, Private key algotithm: {},\n'
                .format(self.private_key_filepath, self.private_key_algorithm)
            + '\tMQTT URL: {}, MQTT port: {}.'.format(self.mqtt_url, self.mqtt_port)
        )


class CloudImplementationBase:
    def __init__(self, cloud_conn_params: CloudConnectionParameters):
        self._cloud_conn_params = cloud_conn_params

        _log.debug('CloudImplementationBase instance created.')

    def create_connection(self) -> int:
        raise NotImplementedError

    def close_connection(self) -> int:
        raise NotImplementedError

    def wait_for_command(self) -> str:
        raise NotImplementedError

    def wait_for_configuration(self) -> str:
        raise NotImplementedError

    def send_event(self, payload) -> int:
        raise NotImplementedError


class Cloud:
    def __init__(self,
        CloudImplCls, cloud_conn_params: CloudConnectionParameters
    ):
        self._cloud_conn_params = cloud_conn_params
        self._cloud_impl: CloudImplementationBase = CloudImplCls(cloud_conn_params)

        _log.debug('Cloud instance created.')
        _log.info(
            'Cloud type: {}, Cloud connection parameters:\n{}'
                .format(type(self._cloud_impl), str(cloud_conn_params)))

    def create_connection(self) -> int:
        return self._cloud_impl.create_connection()

    def close_connection(self) -> int:
        return self._cloud_impl.close_connection()

    def wait_for_command(self) -> str:
        return self._cloud_impl.wait_for_command()

    def wait_for_configuration(self) -> str:
        return self._cloud_impl.wait_for_configuration()

    def send_event(self, payload) -> int:
        return self._cloud_impl.send_event(payload)
