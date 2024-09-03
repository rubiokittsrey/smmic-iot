# this module contains all functions and processes related to the network
import subprocess
import psutil
import socket
import time
import settings
import logging
from utils import log_config, parse_ping, parse_err_ping

from typing import Tuple, Optional

log = log_config(logging.getLogger(__name__))

# check primary interface and see if it has an active ip address
# returns the interface and the ip
def __check_interface__() -> Tuple[str, Optional[str]]:
    interface = settings.APPConfigurations.NETWORK_INTERFACE
    ip = None
    interfaces = psutil.net_if_addrs()
    
    # check if interfaces contains the primary network interface set in settings.yaml
    if interface in interfaces.keys():
        addresses = interfaces[interface]
        log.debug(f'Found interface \'{interface}\' checking for active addresses')
        
        # check if the interface has an active ipv4 address
        # assing address to ip variable
        if not addresses:
            log.error(f'No active ip addresses found for interface \'{interface}\'')
        else:
            for address in addresses:
                if address.family == socket.AF_INET:
                    log.info(f'Interface \'{interface}\' with active IP address {address.address}')
                    ip = address.address
    else:
        log.warning(f'Interface check did not find the primary interface set in app configurations.')

    return interface, ip

# ping the specified host for n amount of times
# returns the ip, packets sent, packets received and the packet loss as well as rtt statistics
def __ping__(host, repeat=1) -> Tuple[str | None, ...]:
    sent = received = loss = rtt_min = rtt_avg = rtt_max = rtt_mdev = errors = time = None

    # repeat the PING command based on repeat parameter
    for i in range(repeat):
        try:
            output = subprocess.check_output(["ping", "-c", "5", host])
            sent, received, loss, rtt_min, rtt_avg, rtt_max, rtt_mdev = parse_ping(output=output)
            log.debug(f'PING {host} - Packets: {sent} sent, {received} received, {loss}% loss - RTT: {rtt_min} (min), {rtt_avg} (avg), {rtt_max} (max), {rtt_mdev} (mdev)')
        except subprocess.CalledProcessError as e:
            output = e.output
            sent, received, loss, errors, time = parse_err_ping(output=output)
            log.error(f"PING {host} - Errors: {errors} - Packets: {sent} sent, {received} received, {loss}% loss - Time: {time}ms")
    
    return sent, received, loss, rtt_min, rtt_avg, rtt_max, rtt_mdev, errors, time

# handles connection problems by timing out processes
# TODO: refactor this function and implement to network check
def __time_out_handler__(function):
    # the default timeout duration on disconnected, ideally this should be 5 minutes
    # value is configured in settings.yaml
    maxTimeouts = settings.APPConfigurations.NETWORK_MAX_TIMEOUTS
    timeOut = settings.APPConfigurations.NETWORK_TIMEOUT

    log.warning(f'Retrying again in {timeOut} seconds. Attemps remaining: {maxTimeouts}')
    time.sleep(timeOut)

    result = None

    for i in range(maxTimeouts):
        result = function()

    while maxTimeouts > 0:
        maxTimeouts = maxTimeouts - 1
        if maxTimeouts == 0:
            log.error(f'Max attemps ({maxTimeouts}) reached, terminating application. Please check the network connectivity of the device.')
            return False
        log.warning(f'Retrying again in {timeOut} seconds. Attemps remaining: {maxTimeouts}')
        time.sleep(timeOut)

    return result

# checks the primary network interface for active ip addresses
# and then pings the gateway to confirm network connectivity
# priamry network interface and gateway are configured in settings.yaml
def network_check() -> bool:
    interface, ip = __check_interface__()
    if not ip:
        return False
    
    log.debug(f'Trying PING with gateway address: {settings.APPConfigurations.GATEWAY}')
    sent, received, packet_loss, rtt_min, rtt_avg, rtt_max, rtt_mdev, errors, time = __ping__(settings.APPConfigurations.GATEWAY)

    if errors:
        log.warning(f'Cannot establish successful ping with gateway {settings.APPConfigurations.GATEWAY}!')
        return False

    #TODO: run internet check to verify internet connectivity

    return True