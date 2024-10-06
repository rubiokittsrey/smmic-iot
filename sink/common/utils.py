import logging as __logging__
import settings
import os
import re
import logging
import multiprocessing
from typing import Tuple, Optional, Dict, List, Any

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
    # checks
    UNVERIFIED = 100
    SUCCESS = 200
    WARNING = 300
    ERROR = 400
    CRITICAL = 500

    # states
    ACTIVE = 250
    INACTIVE = 350
    CONNECTED = 1
    DISCONNECTED = 0
    FAILED = ERROR

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

__log__ = log_config(logging.getLogger(__name__))

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
        settings.dev_mode(True)
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
    BACKGROUND : int = 6 # store in memory until other more important tasks are done

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

    return _priority

# checks if a number is a float or an int
# returns None if neither
def is_num(var) -> type[float | int] | None:
    _type: type[float | int] | None = None

    try:
        int_var = int(var)
        _type = int
    except ValueError:
        pass

    if _type is None:
        try:
            float_var = float(var)
            _type = float
        except ValueError:
            pass

    return _type

# maps the payload from the device reading into a dictionary
# assuming that the shape of the payload (as a string) is:
# -------
# sensor_type;
# device_id;
# timestamp;
# reading:value&
# reading:value&
# reading:value&
# reading:value&
# ...
# -------
def map_sensor_payload(payload: str) -> Dict:
    final: Dict = {}

    # parse the contents of the payload string
    outer_split : List[str] = payload.split(";")
    final.update({
        'SensorType': outer_split[0],
        'Sensor_Node': outer_split[1],
        'timestamp': outer_split[2],
    })

    # parse the data from the 3rd index of the payload split
    data : List[str] = outer_split[3].split("&")

    # remove empty strings in the list
    for i in range(data.count("")):
        data.remove("")

    for value in data:
        # split the key and value of the value string
        x = value.split(":")
        # check the value for a valid num type (int or float)
        _num_check = is_num(x[1])

        if not _num_check:
            final.update({x[0]: x[1]})
        else:
            final.update({x[0]: _num_check(x[1])})

    # if outer_split[0] == 'sensor_type':
    #     data : List = outer_split[3].split(":")
    #     final.update([
    #         ('sensor_type',outer_split[0]),
    #         ('Sensor_Node', outer_split[1]),
    #         ('timestamp', outer_split[2]),
    #         ('soil_moisture', data[0]),
    #         ('humidity', data[1]),
    #         ('temperature', data[2]),
    #         ('battery_level', data[3]),
    #     ])

    return final

# maps the payload from the sink data into a dictionary
# assuming that the shape of the payload (as a string) is:
# ------
# device_id;
# timestamp;
# key:value&
# key:value&
# key:value&
# key:value&
# ..........
# ------
def map_sink_payload(payload: str) -> Dict:
    final: Dict = {}

    outer_split: List[str] = payload.split(';')
    final.update({
        'Sink_Node': outer_split[0],
        'timestamp': outer_split[1]
    })

    data: List[str] = outer_split[2].split("&")

    # remove empty strings in the list
    for i in range(data.count("")):
        data.remove("")

    for value in data:
        # split the key and value of the value string
        x = value.split(":")
        # check the value for a valid num type (int or float)
        _num_check = is_num(x[1])

        if not _num_check:
            final.update({x[0]: x[1]})
        else:
            final.update({x[0]: _num_check(x[1])})

    return final

class SensorAlerts:
    # connection
    CONNECTED = 1
    DISCONNECTED = 0

    # temperature
    HIGH_TEMP = 20
    NORMAL_TEMP = 21
    LOW_TEMP = 22

    # humidity
    HIGH_HUMIDITY = 20
    NORMAL_HUMIDITY = 21
    LOW_HUMIDITY = 22

    # soil moisture
    HIGH_SOIL_MOISTURE = 40
    NORMAL_SOIL_MOISTURE = 40
    LOW_SOIL_MOISTURE = 41

    # maps the payload from the 'smmic/sensor/alert' topic
    # assuming that the shape of the payload (as a string) is:
    # ---------
    # device_id;
    # timestamp;
    # alert_code
    # ---------
    def map_sensor_alert(payload: str) -> Dict | None:
        final: Dict | None

        outer_split: List[str] = payload.split(';')
        final = {'device_id': outer_split[0], 'timestamp': outer_split[1]}

        num_check = is_num(outer_split[2])

        if not num_check:
            __log__.warning(f"{__name__} failed num_check on alert payload: {payload} (non-num alert code)")
            final = None
        else:
            final.update({
                'alert_code': num_check(outer_split[2])
            })

        return final

# helper function to retrieve messages from a queue
# run in use loop.run_in_executor() method to run in non-blocking way
def get_from_queue(queue: multiprocessing.Queue, mod: str) -> Dict | None:
    msg: dict | None = None
    try:
        msg = queue.get(timeout=0.1)
    except Exception as e:
        if not queue.empty():
            __log__.error(f"Unhandled exception raised @ PID {os.getpid()} ({mod}) while getting items from queue: {e}")
        else:
            pass

    return msg