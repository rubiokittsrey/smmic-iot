# this module contains all functions and processes related to the network

# third-party
import subprocess
import psutil
import socket
import time
import logging
from typing import Tuple, Optional

# internal
from utils import logger_config, parse_ping, parse_err_ping, status
from settings import Registry, APPConfigurations

# settings, configurations
alias = Registry.Modules.Network.alias
_log = logger_config(logging.getLogger(__name__))

# check primary interface and see if it has an active ip address
# returns the interface and the ip
def _check_interface() -> Tuple[str, Optional[str]]:
    interface = APPConfigurations.PRIMARY_NET_INTERFACE
    ip = None
    interfaces = psutil.net_if_addrs()
    
    # check if interfaces contains the primary network interface set in settings.yaml
    if interface in interfaces.keys():
        addresses = interfaces[interface]
        _log.debug(f'Found interface \'{interface}\' checking for active addresses')
        
        # check if the interface has an active ipv4 address
        # assing address to ip variable
        if not addresses:
            _log.error(f'No active ip addresses found for interface \'{interface}\'')
        else:
            for address in addresses:
                if address.family == socket.AF_INET:
                    _log.debug(f'Interface \'{interface}\' with active IP address {address.address}')
                    ip = address.address
    else:
        _log.warning(f'Interface check did not find the primary interface set in app configurations.')

    return interface, ip

# ping the specified host for n amount of times
# returns the ip, packets sent, packets received and the packet loss as well as rtt statistics
def _ping(host, repeat=1) -> Tuple[str | None, ...]:
    sent = received = loss = rtt_min = rtt_avg = rtt_max = rtt_mdev = errors = time = None

    # repeat the PING command based on repeat parameter
    for i in range(repeat):
        try:
            output = subprocess.check_output(["ping", "-c", "5", host])
            sent, received, loss, rtt_min, rtt_avg, rtt_max, rtt_mdev = parse_ping(output=output)
            _log.debug(f'PING {host} - Packets: {sent} sent, {received} received, {loss}% loss - RTT: {rtt_min} (min), {rtt_avg} (avg), {rtt_max} (max), {rtt_mdev} (mdev)')
        except subprocess.CalledProcessError as e:
            output = e.output
            sent, received, loss, errors, time = parse_err_ping(output=output)
            _log.error(f"PING {host} - Errors: {errors} - Packets: {sent} sent, {received} received, {loss}% loss - Time: {time}ms")
    
    return sent, received, loss, rtt_min, rtt_avg, rtt_max, rtt_mdev, errors, time

# handles connection problems by timing out processes
# NOTE: unimplemented
# TODO: refactor this function and implement to network check
def _time_out_handler(function):
    # the default timeout duration on disconnected, ideally this should be 5 minutes
    # value is configured in settings.yaml
    maxTimeouts = APPConfigurations.NETWORK_MAX_TIMEOUT_RETRIES
    timeOut = APPConfigurations.NETWORK_TIMEOUT

    _log.warning(f'Retrying again in {timeOut} seconds. Attemps remaining: {maxTimeouts}')
    time.sleep(timeOut)

    result = None

    for i in range(maxTimeouts):
        result = function()

    while maxTimeouts > 0:
        maxTimeouts = maxTimeouts - 1
        if maxTimeouts == 0:
            _log.error(f'Max attemps ({maxTimeouts}) reached, terminating application. Please check the network connectivity of the device.')
            return False
        _log.warning(f'Retrying again in {timeOut} seconds. Attemps remaining: {maxTimeouts}')
        time.sleep(timeOut)

    return result

# checks the primary network interface for active ip addresses
# and then pings the gateway to confirm network connectivity
# priamry network interface and gateway are configured in settings.yaml
def network_check() -> int:
    interface, ip = _check_interface()
    if not ip:
        return status.FAILED
    
    _ping_loss_tolerance = 3 # the amount of loss (out of 5) that can be tolerated

    _log.debug(f'Trying PING with gateway address: {APPConfigurations.GATEWAY}')
    sent, received, packet_loss, rtt_min, rtt_avg, rtt_max, rtt_mdev, errors, time = _ping(APPConfigurations.GATEWAY)

    if errors:
        _log.warning(f'Cannot establish successful ping with gateway {APPConfigurations.GATEWAY}')
        return status.FAILED
    elif packet_loss:
        if int(packet_loss) >= (_ping_loss_tolerance * 2) * 10:
            _log.warning(f'PING request to gateway {APPConfigurations.GATEWAY} returned with packet loss higher than ping loss tolerance ({(_ping_loss_tolerance * 2) * 10}%)')
            return status.FAILED

    return status.SUCCESS

def api_check() -> int:
    # TODO: implement api check
    return 0