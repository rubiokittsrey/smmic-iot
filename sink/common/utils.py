import logging as __logging__
import settings
import os
import re
from typing import Tuple, Optional
import logging

# do not use
def pretty_print(message, ):
    print(f'')

log_directory = settings.APPConfigurations.LOG_FILE_DIRECTORY
log_file = settings.APPConfigurations.LOG_FILE_NAME
os.makedirs(log_directory, exist_ok=True)
log_path = os.path.join(log_directory, log_file)

# LOG VARIABLES (HANDLERS, FORMATTER)
__LOGGER_LIST__ = []
__LOG_FILE_HANDLER__ = __logging__.FileHandler(log_path)
__CONSOLE_HANDLER__ = __logging__.StreamHandler()
__LOG_FORMATTER__ = __logging__.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class status:
    SUCCESS = 200
    ERROR = 400
    WARNING = 300
    CRITICAL = 500
    ACTIVE = SUCCESS
    INACTIVE = WARNING
    FAILED = ERROR
    CONNECTED = ACTIVE
    DISCONNTECTED = INACTIVE

# LOGGING UTILITIES ------------------------------------------------------------------------------------
# returns the logger object from caller with fromatter, console handler and file handler
def log_config(logger) -> __logging__.Logger:
    global __LOGGER_LIST__
    __LOGGER_LIST__.append(logger)
    logger.setLevel(__logging__.DEBUG)

    console_handler = __CONSOLE_HANDLER__
    logs_handler = __LOG_FILE_HANDLER__

    console_handler.setFormatter(__LOG_FORMATTER__)
    logs_handler.setFormatter(__LOG_FORMATTER__)

    logger.addHandler(console_handler)
    logger.addHandler(logs_handler) if settings.ENABLE_LOG_TO_FILE else None

    return logger

def set_logging_configuration():
    for logger in __LOGGER_LIST__:
        logger.setLevel(settings.LOGGING_LEVEL)
        logger.removeHandler(__LOG_FILE_HANDLER__) if not settings.ENABLE_LOG_TO_FILE else None

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
    sent = received = errors = time = None

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

    #parsed data
    sent = packet_stats_match.group(1) if packet_stats_match else None
    received = packet_stats_match.group(2) if packet_stats_match else None
    loss = packet_loss_match.group(1) if packet_loss_match else None
    errors = errors_match.group(1) if errors_match else None
    time = time_match.group(1) if time_match else None

    return sent, received, loss, errors, time

# application modes
class Modes:
    def dev():
        settings.set_logging_level(logging.DEBUG)
        settings.enable_log_to_file(False)
        set_logging_configuration()
    def normal():
        settings.set_logging_level(logging.WARNING)
        set_logging_configuration()
    def info():
        settings.set_logging_level(logging.INFO)
        set_logging_configuration()
    def debug():
        settings.set_logging_level(logging.DEBUG)
        set_logging_configuration()