# contains all the processes and functions related to the mosquitto service running on the raspberry pi
import subprocess
import logging
from typing import Literal

from utils import status, log_config
import settings

log = log_config(logging.getLogger(__name__))

def mqtt_status_check() -> status:
    try:
        result = subprocess.run(
                ['systemctl', 'status', 'mosquitto'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True
            )
        if "Active: active (running)" in result.stdout:
            log.info(f'MOSQUITTO Broker status: active')
            # TODO: implement checking which port mosquitto.service is listening to
            log.warning(f'Cannot identify the port mosquitto.service is listening to. Application will proceed to use default port {settings.Broker.PORT}')
            return status.ACTIVE
        elif "Active: inactive (dead)" in result.stdout:
            log.error(f'mosquitto.service status: dead! Please start the mosquitto.service and then rerun status check')
            return status.INACTIVE
        elif "Unit mosquitto.service could not be found" in result.stderr:
            log.error(f'mosquitto.service could not be found on this environment, cannot verify status')
            return status.FAILED
    except Exception as e:
        #TODO: handle exception properly!
        log.info(f'An unhandled exception has occured: {e}')
        return status.FAILED