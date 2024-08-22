# the main python script managing all scripts within /src directory
import os
import settings
import concurrent.futures
import time
import logging

# TESTING IMPORTS BELOW
import src.hardware as hardware
import src.api as api
from utils import log_config

log = log_config(logging.getLogger(__name__))

if __name__ == "__main__":
    if(not settings.DevConfigs.ENABLE_LOG_TO_FILE):
        print('Logging to file disabled\n')
    os.system('clear')
    with concurrent.futures.ThreadPoolExecutor() as executor:
        network_task = executor.submit(hardware.network.network_monitor)