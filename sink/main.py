# the main python script managing all scripts within /src directory

import os

# TESTING IMPORTS BELOW
import smmic.api as api
import smmic.data as data
import smmic.hardware as hardware
import smmic.mqtt as mqtt

if __name__ == "__main__":
    os.system('clear')
    hardware.network.monitor_network()