# the main python script managing all scripts within /src directory

import os

# TESTING IMPORTS BELOW
import src.hardware as hardware

if __name__ == "__main__":
    os.system('clear')
    hardware.network.monitor_network()