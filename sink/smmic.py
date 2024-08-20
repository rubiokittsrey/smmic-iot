# the main python script managing all scripts within /src directory

import os
import settings

# TESTING IMPORTS BELOW
import src.hardware as hardware

if __name__ == "__main__":
    if(not settings.DevConfigs.ENABLE_LOG_TO_FILE):
        print('Logging to file disabled\n')

    os.system('clear')
    hardware.network.network_monitor()

def main():
    #main function here
    os.system('clear')