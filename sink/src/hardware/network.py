import subprocess
import psutil
import socket
import time
import settings
import argparse

from utils import logs

# the default timeout duration on disconnected, ideally this should be 5 minutes
# this is only for development purposes
# the value for this should come fro mthe settings.yaml

# ping the specified host for n amount of times
def __ping__(host, repeat=1):
    if(not repeat):
        repeat = 1
    results = []
    for i in range(repeat):
        try:
            output = subprocess.check_output(["ping", "-c", "1", host])
            logs.info(output.decode('utf-8'))
            results.append(True)
        except subprocess.CalledProcessError:
            results.append(False)
            output = subprocess.CalledProcessError
            logs.error(f"Host {host} is unreachable")
        time.sleep(1.5)
    print(results)
    return results

# check network connectivity by checking if any interface is UP and has an ip address, returns None if not connected
# returns a list of the interfaces with ip addresses if connected
def __check_interface__():
    addresses = {}
    for interface, addrs in psutil.net_if_addrs().items():
        addresses[interface] = [addr.address for addr in addrs if addr.family == socket.AF_INET]

    for interface, ips in addresses.items():
        if interface != 'lo':
            if not ips:
                logs.warning(f'network.__is_connected__() returned without an IP on interface \'{interface}\' sleeping for {settings.APPConfigurations.NETWORK_TIMEOUT} seconds\n')
                time.sleep(settings.APPConfigurations.NETWORK_TIMEOUT)
            for ip in ips:
                logs.success(f'Active Interface \'{interface}\' with IP {ip}')
                return True

# monitor network connection
def monitor_network():

    maxTimeouts = settings.APPConfigurations.NETWORK_MAX_TIMEOUTS
    while maxTimeouts != 0:
        maxTimeouts = maxTimeouts - 1
        if __check_interface__() :
            break;
        if maxTimeouts == 0:
            logs.error(f'Max timeouts reached, terminating now')
            return False
        
    # host = "8.8.8.8" # Google DNS
    # if __ping__(host):
    #     print(f"Network is UP - {host} is reachable.")
    # else:
    #     print(f"Network is DOWN - {host} is not reachable.")
    
    # import subprocess
# 
# try:
    # output = subprocess.check_output(["ping", "-c", "1", "8.8.8.8"])
    # print(output.decode('utf-8'))
# except subprocess.CalledProcessError as e:
    # print(f"Command failed with return code {e.returncode}")