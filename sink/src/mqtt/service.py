# contains all the processes and functions related to the mosquitto service running on the raspberry pi
import subprocess
import logging
from typing import Literal

from utils import status, logger_config
from settings import Broker, Registry

# settings, configurations
alias = Registry.Modules.Service.alias
_log = logger_config(logging.getLogger(__name__))

def mqtt_status_check() -> int:
    try:
        result = subprocess.run(
                ['systemctl', 'status', 'mosquitto'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True
            )
        if "Active: active (running)" in result.stdout:
            # TODO: implement checking which port mosquitto.service is listening to
            _log.warning(f'Cannot identify the port mosquitto.service is listening to. Application will proceed to use default port {Broker.PORT}')
            return status.ACTIVE
        elif "Active: inactive (dead)" in result.stdout:
            _log.error(f'mosquitto.service status: dead! Please start the mosquitto.service and then rerun status check')
            return status.INACTIVE
        elif "Unit mosquitto.service could not be found" in result.stderr:
            _log.error(f'mosquitto.service could not be found on this environment, cannot verify status')
            return status.FAILED
    except Exception as e:
        #TODO: handle exception properly!
        _log.info(f'An unhandled exception has occured: {e}')
        return status.FAILED
    
    return status.FAILED