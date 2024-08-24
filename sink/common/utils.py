import logging as __logging__
import settings
import os
import re
from typing import Tuple, Optional
# do not use
def pretty_print(message, ):
    print(f'')

def __init_logs_handlers__(log_path: str) -> Tuple[__logging__.StreamHandler, Optional[__logging__.FileHandler]]: 
    logs_handler = __logging__.FileHandler(log_path)
    console_handler = __logging__.StreamHandler()

    # console_handler.setLevel(__logging__.DEBUG)
    # logs_handler.setLevel(__logging__.DEBUG)

    formatter = __logging__.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    logs_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    return console_handler, logs_handler

# returns the logger object from caller with fromatter, console handler and file handler
def log_config(logger) -> __logging__.Logger:
    logger.setLevel(__logging__.DEBUG)
    log_directory = '/home/rubiokittsrey/Projects/smmic-iot/sink/common/logs/'
    log_file = 'smmic.log'
    os.makedirs(log_directory, exist_ok=True)
    log_path = os.path.join(log_directory, log_file)

    console_handler, logs_handler = __init_logs_handlers__(log_path)
    logger.addHandler(console_handler)
    logger.addHandler(logs_handler) if settings.DevConfigs.ENABLE_LOG_TO_FILE else None

    return logger

# parses and returns the packet loss, and rtt min, avg, max and mdev from a ping output
# just for pretty ping logs, really
def parse_ping(output) -> Tuple[str, ...]:
    output_decoded = output.decode('utf-8')

    # patterns
    packet_stats = re.compile(r'(\d+) packets transmitted, (\d+) received')
    packet_loss = re.compile(r'(\d+)% packet loss')
    rtt = re.compile(r'rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms')

    packet_stats_match = packet_stats.search(output_decoded)
    packet_loss_match = packet_loss.search(output_decoded)
    rtt_match = rtt.search(output_decoded)
    
    # parsed data
    packets_sent = packet_stats_match.group(1) if packet_stats_match else None
    packets_recieved = packet_stats_match.group(2) if packet_stats_match else None
    packet_loss = packet_loss_match.group(1) if packet_loss_match else None
    rtt_min = rtt_match.group(1) if rtt_match else None
    rtt_avg = rtt_match.group(2) if rtt_match else None
    rtt_max = rtt_match.group(3) if rtt_match else None
    rtt_mdev = rtt_match.group(4) if rtt_match else None

    return packets_sent, packets_recieved, packet_loss, rtt_min, rtt_avg, rtt_max, rtt_mdev

def parse_err_ping(output) -> Tuple[str, ...]:
    output_decoded = output.decode('utf-8')
    
    #patterns
    packet_stats = re.compile(r'(\d+) packets transmitted, (\d+) received')
    packet_loss = re.compile(r'(\d+)% packet loss')
    errors = re.compile(r'\+(\d+) errors')
    time = re.compile(r'time ([\d\.]+)')

    packet_stats_match = packet_stats.search(output_decoded)
    packet_loss_match = packet_loss.search(output_decoded)
    errors_match = errors.search(output_decoded)
    time_match = time.search(output_decoded)

    sent = received = errors = time = None

    #parsed data
    if (packet_stats_match):
        sent = packet_stats_match.group(1)
        received = packet_stats_match.group(2)

    if (packet_loss_match):
        loss = packet_loss_match.group(1)
        
    if (errors_match):
        errors = errors_match.group(1)

    if (time_match):
        time = time_match.group(1)

    print(errors)

    return sent, received, loss, errors, time