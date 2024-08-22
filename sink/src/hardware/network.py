# this module contains all functions and processes related to the network

import subprocess
import psutil
import socket
import time
import settings
import argparse
import logging
from utils import log_config, parse_ping
import asyncio

log = log_config(logging.getLogger(__name__))

# ping the specified host for n amount of times
# returns an array of bools specifying the amount of times (and the order) the repeating pings have been successful
def __ping__(host, repeat=1):
    results = []
    for i in range(repeat):
        try:
            output = subprocess.check_output(["ping", "-c", "5", host])
            ip, sent, received, packet_loss, rtt_min, rtt_avg, rtt_max, rtt_mdev = parse_ping(output) # parse output
            log.info(f'PING {host} - Packets: {sent} sent, {received} received, {packet_loss}% loss - RTT: {rtt_min} (min), {rtt_avg} (avg), {rtt_max} (max), {rtt_mdev} (mdev)')
            results.append({'ip': host, 'sent': sent, 'received': received, 'loss': packet_loss, 'min': rtt_min, 'avg': rtt_avg, 'max': rtt_max, 'mdev': rtt_mdev})
        except subprocess.CalledProcessError as e:
            log.error(f"PING {host} - Exit code: {e.returncode} - {e.stderr}")
            # TODO: probably perform a network check when this happens
            results.append(False)
    return results

# check network connectivity by checking if any interface is UP and has an ip address, returns None if not connected
# returns a list of the interfaces with ip addresses if connected
def __check_interface__():
    log.info(f'Searching interfaces for active IP address')
    addresses = {}
    for interface, addrs in psutil.net_if_addrs().items():
        addresses[interface] = [addr.address for addr in addrs if addr.family == socket.AF_INET]

    for interface, ips in addresses.items():
        if interface != 'lo':
            if not ips:
                log.warning(f'network.__is_connected__() returned without an IP on interface \'{interface}\'')
                return False
            for ip in ips:
                log.info(f'Active interface \'{interface}\' detected with IP {ip}')
                return True

# handles connection problems by timing out processes
def __time_out_handler__(function):
    # the default timeout duration on disconnected, ideally this should be 5 minutes
    # value is configured in settings.yaml
    maxTimeouts = settings.APPConfigurations.NETWORK_MAX_TIMEOUTS
    timeOut = settings.APPConfigurations.NETWORK_TIMEOUT

    log.warning(f'Retrying again in {timeOut} seconds. Attemps remaining: {maxTimeouts}')
    time.sleep(timeOut)

    while not function():
        maxTimeouts = maxTimeouts - 1
        if maxTimeouts == 0:
            log.error(f'Max attemps ({settings.APPConfigurations.NETWORK_MAX_TIMEOUTS}) reached, terminating application. Please check the network connectivity of the device.')
            return False
        log.warning(f'Retrying again in {timeOut} seconds. Attemps remaining: {maxTimeouts}')
        time.sleep(timeOut)

    return True

# monitor network connection

# performs checks on interfaces, pings etc. on network startup
# returns 'false' if a critical function returns with failure
# NOTE: use this function to check on network status whenever a network operation fails
def __init_network__():
    # interfaces check
    # looks for interfaces other than 'lo' and checks if any is UP
    if(not __check_interface__()):
        if not __time_out_handler__(__check_interface__):
            return False
      
    log.info(f'Testing network connectivity with access point {settings.APPConfigurations.GATEWAY}')  
    if(not __ping__(settings.APPConfigurations.GATEWAY)): #ping gateway to check network connectivity
        if not __time_out_handler__(__ping__):
            return False
    
    log.info(f'Testing internet connectivity using \'google.com\'')
    if(not __ping__('google.com')):
        log.warning(f'PING \'google.com\' returned with error, connection to the internet cannot be established')

    return True

def network_monitor():
    if (not __init_network__()):
        log.critical(f'Terminating smmic.py main network() function')
        return False
    else:
        return True