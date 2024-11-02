from __future__ import annotations

import logging as _logging
import settings
import os
import re
import logging
import multiprocessing
import queue
from typing import Tuple, Optional, Dict, List, Any

# do not use
def pretty_print(message, ):
    print(f'')

log_directory = settings.APPConfigurations.LOG_FILE_DIRECTORY
log_file = settings.APPConfigurations.LOG_FILE_NAME
os.makedirs(log_directory, exist_ok=True)
log_path = os.path.join(log_directory, log_file)

# LOG VARIABLES (HANDLERS, FORMATTER)
_LOGGER_LIST = []
_LOG_FILE_HANDLER = _logging.FileHandler(log_path)
_CONSOLE_HANDLER = _logging.StreamHandler()
_LOG_FORMATTER = _logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_LOG_FORMATTER_VERBOSE = _logging.Formatter('%(asctime)s - %(levelname)s - %(message)s - %(processName)s (%(process)d) -> %(module)s', datefmt='%Y-%m-%d %H:%M:%S')

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

    # task status
    PENDING = 1
    RUNNING = 2
    COMPLETE = 3

# the logging configurations
# returns the logger object from caller with fromatter, console handler and file handler
def log_config(logger) -> _logging.Logger:
    global _LOGGER_LIST
    _LOGGER_LIST.append(logger)
    logger.setLevel(_logging.DEBUG)

    console_handler = _CONSOLE_HANDLER
    logs_handler = _LOG_FILE_HANDLER

    console_handler.setFormatter(_LOG_FORMATTER_VERBOSE)
    logs_handler.setFormatter(_LOG_FORMATTER_VERBOSE)

    logger.addHandler(console_handler)
    logger.addHandler(logs_handler) if settings.ENABLE_LOG_TO_FILE else None

    return logger

_logs = log_config(logging.getLogger(__name__))

def set_logging_configuration():
    for logger in _LOGGER_LIST:
        logger.setLevel(settings.LOGGING_LEVEL)
        logger.removeHandler(_LOG_FILE_HANDLER) if not settings.ENABLE_LOG_TO_FILE else None

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
    @staticmethod
    def dev():
        settings.dev_mode(True)
        settings.set_logging_level(logging.DEBUG)
        settings.enable_log_to_file(False)
        set_logging_configuration()

    @staticmethod
    def normal():
        settings.set_logging_level(logging.WARNING)
        set_logging_configuration()
    
    @staticmethod
    def info():
        settings.set_logging_level(logging.INFO)
        set_logging_configuration()

    @staticmethod
    def debug():
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

    if _type is None:
        _logs.warning(f"Failed num_check at {__name__}: {var}")

    return _type

# maps the payload from sensor devices
# assuming that the shape of the payload (as a string) is:
#
# sensor_type;
# device_id;
# timestamp;
# reading:value&
# reading:value&
# reading:value&
# reading:value&
# ...
#
class SensorData:
    def __init__(self, sensor_type, device_id, timestamp, readings, payload):
        self.sensor_type = sensor_type
        self.device_id = device_id
        self.timestamp = timestamp
        self.readings = readings
        self.payload = payload

    # soil moisture sensor type
    class soil_moisture:
        def __init__(self, soil_moisture, humidity, temperature, battery_level):
            self.soil_moisture = soil_moisture
            self.humidity = humidity
            self.temperature = temperature
            self.battery_level = battery_level

    @staticmethod
    def map_sensor_payload(payload: str) -> Dict:
        final: Dict = {}

        # parse the contents of the payload string
        outer_split : List[str] = payload.split(";")
        final.update({
            'sensor_type': outer_split[0],
            'device_id': outer_split[1],
            'timestamp': outer_split[2],
            'payload': payload
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

    @classmethod
    def from_payload(cls, payload: str) -> SensorData:
        b_map = SensorData.map_sensor_payload(payload)
        readings = None

        if b_map['sensor_type'] == 'soil_moisture':
            readings = SensorData.soil_moisture(
                soil_moisture=b_map['soil_moisture'],
                humidity=b_map['humidity'],
                temperature=b_map['temperature'],
                battery_level=b_map['battery_level']
            )
            b_map.update({'readings': readings})
        
        f_map = {
            'sensor_type': b_map['sensor_type'],
            'device_id': b_map['device_id'],
            'payload': b_map['payload'],
            'readings': b_map['readings'],
            'timestamp': b_map['timestamp']
        }

        _self = cls(**f_map)
        return _self

# maps the payload from the sink data
# assuming that the shape of the payload (as a string) is:
#
# device_id;
# timestamp;
# key:value&
# key:value&
# key:value&
# key:value&
# ...
#
class SinkData:
    # connected clients, connected total, sub count
    # bytes sent, bytes received, messages sent, messages received
    def __init__(self,
                 payload,
                 timestamp,
                 connected_clients,
                 total_clients,
                 sub_count,
                 bytes_sent,
                 bytes_received,
                 messages_sent,
                 messages_received,
                 battery_level,
                 device_id
                 ):
        self.device_id = device_id
        self.payload = payload
        self.timestamp = timestamp
        self.connected_clients = connected_clients
        self.total_clients = total_clients
        self.sub_count = sub_count
        self.bytes_sent = bytes_sent
        self.bytes_received = bytes_received
        self.messages_sent = messages_sent
        self.messages_received = messages_received
        self.battery_level = battery_level

    @staticmethod
    def map_sink_payload(payload: str) -> Dict:
        # keys --> (as of oct 18, 2024)
        # raw_payload: the (unmapped) string payload
        # Sink_Node: the sink node device id,
        # timestamp: timestamp of the payload, not when it was received,
        # connected_clients: currently connected clients,
        # total_clients: disconnected and connected clients,
        # sub_count: total subscription count of the entire mqtt network kept track by the broker,
        # bytes_sent,
        # bytes_received,
        # messages_sent,
        # messages_received,
        # battery_level

        final: Dict = {}

        outer_split: List[str] = payload.split(';')
        final.update({
            'device_id': outer_split[0],
            'timestamp': outer_split[1],
            'payload': payload
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

    # TODO: properly implement this function
    @classmethod
    def from_payload(cls, payload: str) -> SinkData:
        b_map = SinkData.map_sink_payload(payload)

        try:
            _self = cls(**b_map)
        except Exception as e:
            _logs.error(f"Unhandled exception raised while creating a new SinkData object at {__name__}")

        return _self

class SensorAlerts:
    # connection
    CONNECTED = 1
    DISCONNECTED = 0

    # temperature
    HIGH_TEMPERATURE = 30
    NORMAL_TEMPERATURE = 31
    LOW_TEMPERATURE = 32

    # humidity
    HIGH_HUMIDITY = 20
    NORMAL_HUMIDITY = 21
    LOW_HUMIDITY = 22

    # soil moisture
    HIGH_SOIL_MOISTURE = 40
    NORMAL_SOIL_MOISTURE = 41
    LOW_SOIL_MOISTURE = 42

    # maps the payload from the 'smmic/sensor/alert' topic
    # assuming that the shape of the payload (as a string) is:
    # ---------
    # device_id;
    # timestamp;
    # alert_code
    # ---------
    @staticmethod
    def map_sensor_alert(payload: str) -> Dict | None:
        final: Dict | None

        outer_split: List[str] = payload.split(';')
        final = {'device_id': outer_split[0], 'timestamp': outer_split[1]}

        num_check = is_num(outer_split[2])

        if not num_check:
            final = None
        else:
            final.update({
                'alert_code': num_check(outer_split[2])
            })

        return final

# helper function to retrieve messages from a queue
# run using loop.run_in_executor() method to run in non-blocking way
def get_from_queue(queue: multiprocessing.Queue, name: str) -> Dict | None:
    msg: dict | None = None
    try:
        msg = queue.get(timeout=0.1)
    except Exception as e:
        if not queue.empty():
            _logs.error(f"Unhandled exception raised while getting items from queue ({name}): {str(e)}")

    return msg

def put_to_queue(queue:multiprocessing.Queue, name:str, data: Any) -> Tuple[int, Any]:
    buffer = None
    result = status.FAILED
    try:
        queue.put_nowait(obj=data)
        result = status.SUCCESS
    except Exception as e:
        buffer = data
        _logs.error(f"Unhandled exception raised while putting items to queue ({name}): {str(e)}")

    return result, buffer

# helper class with functions for handling common exceptions
class ExceptionsHandler:

    class event_loop:
        
        @staticmethod
        def alrd_running(name: str, pid: int, err: str):
            _logs.error(f"Loop is already running ({name} at PID {pid}): {err}")

        @staticmethod
        def unhandled(name: str, pid: int, err: str):
            _logs.error(f"Failed to set new event loop ({name} at PID {pid}): {err}")