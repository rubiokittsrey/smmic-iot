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
    DISCONNECTED = INACTIVE

# the logging configurations
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
def parse_ping(output) -> Tuple[str | None, ...]:
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

def parse_err_ping(output) -> Tuple[str | None, ...]:
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
    def dev(): #type: ignore
        settings.set_logging_level(logging.DEBUG)
        settings.enable_log_to_file(False)
        set_logging_configuration()
    def normal(): #type: ignore
        settings.set_logging_level(logging.WARNING)
        set_logging_configuration()
    def info(): #type: ignore
        settings.set_logging_level(logging.INFO)
        set_logging_configuration()
    def debug(): #type: ignore
        settings.set_logging_level(logging.DEBUG)
        set_logging_configuration()

# the priority class designed for tasks
class priority:
    CRITICAL : int = 1 # most urgent tasks, above all else (irrigation alert, system errors etc.)
    MAJOR : int  = 2 # important tasks (minor errors, network absence etc.)
    MODERATE : int = 3 # normal routines (api requests, etc.)
    MINOR : int = 4
    BLOCKING : int = 5 # tasks that require all other tasks to halt or pause
    BACKGROUND : int = 0 # store in memory until other more important tasks are done

# TODO: this code could be better
# sets the task priority based on the topic that it came from
def set_priority(topic: str) -> int | None:
    _split = topic.split("/")
    _priority: int | None = None

    # remove any empty string occurence
    _empty_str_count = _split.count("")
    for i in range(_empty_str_count):
        _split.remove("")

    # dev topics
    if _split[0] == "dev":

        if _split[1] == "test":
            _priority = priority.MINOR

    if _split[0] == "smmic":

        # irrigation sub topic
        if _split[1] == "irrigation":
            _priority = priority.MAJOR

        # sink node sub topics
        if _split[1] == "sink":
            
            # alerts have major priority
            if _split[2] == "alert":
                _priority = priority.MAJOR

            # TODO: other sink sub topics here

        if _split[1] == "sensor":
            
            if _split[2] == "alert":
                _priority = priority.MAJOR

            if _split[2] == "data":
                _priority = priority.MODERATE
                
    #     # sensor subtopics
    #     if _split[1] == "sensor":
    #         _priority = priority.

    return _priority