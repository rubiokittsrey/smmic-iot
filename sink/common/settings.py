# this module contains the project settings, configurations, constants, all loaded from configs.yaml
# configs.yaml is gitignored by default
import os
import yaml
import logging
from dotenv import load_dotenv
from typing import Tuple, List, Any

# get configurations from settings.yaml
spath = os.path.join(os.path.dirname(__file__), '../settings.yaml')
with open(spath, 'r') as sfile:
    settings_yaml = yaml.safe_load(sfile)
__app_net_configs__ = settings_yaml["app_configurations"]["network"] # the application network configurations
__test_configs__ = settings_yaml["app_configurations"]["tests"] # testing configurations
__dev_configs__ = settings_yaml["dev_configs"]
__hardware_configs__ = settings_yaml["hardware_configurations"]

# load the .env variables
envpath = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(envpath)

# get variables from the .env file
def __var_from_env__(key: str) -> Any:
    var = os.getenv(key)
    if var:
        return var

# global vars
LOGGING_LEVEL = logging.DEBUG
ENABLE_LOG_TO_FILE =  __dev_configs__["enable_log_to_file"]
__DEV_MODE__ = False

def set_logging_level(level: int) -> None:
    global LOGGING_LEVEL
    LOGGING_LEVEL = level

def enable_log_to_file(value: bool) -> None:
    global ENABLE_LOG_TO_FILE
    ENABLE_LOG_TO_FILE = value

def dev_mode(val: bool) -> None:
    global __DEV_MODE__
    __DEV_MODE__ = val

def __get_dev_mode__() -> bool:
    return __DEV_MODE__
DEV_MODE = __get_dev_mode__()

# development configurations
# class DevConfigs:


# application configurations 
class APPConfigurations:
    GLOBAL_SEMAPHORE_COUNT : int = settings_yaml["app_configurations"]["global_semaphore_count"]

    MQTT_PW : str = settings_yaml["app_configurations"]["mqtt_pwd"]
    MQTT_USERNAME : str = settings_yaml["app_configurations"]["mqtt_username"]

    CLIENT_ID : str = settings_yaml["app_configurations"]["client_id"]
    PRIMARY_NET_INTERFACE : str = __app_net_configs__["primary_interface"]
    SRC_PATH : str = __test_configs__["src_path"]
    GATEWAY : str = __app_net_configs__["gateway"]
    NET_CHECK_INTERVALS = __app_net_configs__["network_check_intervals"] * 60
    NETWORK_TIMEOUT : int = __app_net_configs__["timeout"]
    NETWORK_MAX_TIMEOUT_RETRIES : int = __app_net_configs__["max_connection_timeouts"]

    #logging
    LOG_FILE_DIRECTORY : str = __dev_configs__["log_file_directory"]
    LOG_FILE_NAME : str = __dev_configs__["log_file_name"]

# api base url, enpoints
class APIRoutes:
    BASE_URL : str = __var_from_env__("API_URL")
    TEST_URL : str = __var_from_env__("API_TEST_URL")
    SINK_DATA : str = __var_from_env__("SINK_DATA")
    SENSOR_DATA : str = __var_from_env__("SENSOR_DATA")
    HEADERS : str = settings_yaml["headers"]

# api configurations
class APIConfigs:
    SECRET_KEY : str = __var_from_env__("SECRET_KEY")

# mqtt broker configuration
class Broker:
    HOST : str = __var_from_env__("BROKER_HOST_ADDRESS")
    PORT : int = int(__var_from_env__("BROKER_PORT"))
    ROOT_TOPIC : str = __var_from_env__("ROOT_TOPIC")

# mqtt dev topics
class DevTopics:
    TEST = "/dev/test"

class Channels:
    IRRIGATION = __hardware_configs__["irrigation_channel"]

# mqtt functional topics
class Topics:
    ADMIN_SETTINGS : str = __var_from_env__("ADMIN_SETTINGS_TOPIC")
    ADMIN_COMMANDS : str = __var_from_env__("ADMIN_COMMANDS_TOPIC")
    SENSOR_DATA : str = __var_from_env__("SENSOR_DATA_TOPIC")
    SENSOR_ALERT : str = __var_from_env__("SENSOR_ALERT_TOPIC")
    SINK_DATA : str = __var_from_env__("SINK_DATA_TOPIC")
    SINK_ALERT : str = __var_from_env__("SINK_ALERT_TOPIC")
    SYS_BYTES_RECEIVED : str = __var_from_env__("BROKER_BYTES_RECEIVED")
    SYS_BYTES_SENT : str = __var_from_env__("BROKER_BYTES_SENT")
    SYS_CLIENTS_CONNECTED : str = __var_from_env__("BROKER_CLIENTS_CONNECTED")
    SYS_CLIENTS_TOTAL : str = __var_from_env__("BROKER_CLIENTS_TOTAL")
    SYS_MESSAGES_RECEIVED : str = __var_from_env__("BROKER_MESSAGES_RECEIVED")
    SYS_MESSAGES_SENT : str = __var_from_env__("BROKER_MESSAGES_SENT")
    SYS_SUB_COUNT : str = __var_from_env__("BROKER_SUBSCRIPTIONS_COUNT")
    IRRIGATION : str = __var_from_env__("IRRIGATION_TOPIC")
    
    def get_topics() -> Tuple[List[str], List[str]]:
        _topics: List[str] = []
        _sys_topics: List[str] = []

        for key, value in vars(Topics).items():
            if not value or type(value) != str:
                continue
            if not key.startswith("__"):
                topic_value = getattr(Topics, key)
                if key.startswith("SYS"):
                    _sys_topics.append(topic_value)
                else:
                    _topics.append(topic_value)

        return _topics, _sys_topics
                    

    # def data_topics() -> List[str]: # type: ignore
    #     _topics: List[str] = []

    #     for key, value in vars(Topics).items():
    #         if not value or type(value) != str:
    #             continue
    #         if not key.startswith("__"):
    #             topic_value = getattr(Topics, key)
    #             if key.count("DATA") > 0 or key.count()

    #     return _topics, _sys_topics

# returns two lists of ** all ** available topics
# one for application topics the other for system topics
# def get_topics() -> Tuple[list, list]:
#     _topics: List[str] = []

#     _topic_lists : List[str] = [
#         Topics.ADMIN_SETTINGS,
#         Topics.ADMIN_COMMANDS,
#         Topics.SENSOR_DATA,
#         Topics.SENSOR_ALERT,
#         Topics.SINK_DATA,
#         Topics.SINK_ALERT
#         ]

#     # go over each topic list, and then over each topic
#     # then insert the root topic before the subtopic
#     for _topic in _topic_lists:
#         _topics.append(f"{Broker.ROOT_TOPIC}{_topic}")
    
#     # TODO: see what $SYS topics to add for sink node data
#     # return this with app_topics when thats done ^
#     _sys_topics = ["$SYS/broker/load/bytes/sent", "$SYS/broker/clients/connected"]

#     return _topics, []