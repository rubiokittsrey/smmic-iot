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

# load the .env variables
envpath = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(envpath)

# get topic lists from the .env file
def __topics_from_env__(key: str) -> List[str]:
    topics_str = os.getenv(key)
    topics: List[str]
    
    if topics_str:
        topics = []
        topics += topics_str.split(',')
        
    for i in range(topics.count("")):
        topics.remove("")
    
    return topics

# get variables from the .env file
def __var_from_env__(key: str) -> Any:
    var = os.getenv(key)

    if var:
        return var
    
# global vars
LOGGING_LEVEL = logging.DEBUG
ENABLE_LOG_TO_FILE =  __dev_configs__["enable_log_to_file"]

def set_logging_level(level: int) -> None:
    global LOGGING_LEVEL
    LOGGING_LEVEL = level

def enable_log_to_file(value: bool) -> None:
    global ENABLE_LOG_TO_FILE
    ENABLE_LOG_TO_FILE = value

# development configurations
# class DevConfigs:


# application configurations 
class APPConfigurations:
    MQTT_PW = settings_yaml["app_configurations"]["mqtt_pwd"]
    MQTT_USERNAME = settings_yaml["app_configurations"]["mqtt_username"]

    CLIENT_ID = settings_yaml["app_configurations"]["client_id"]
    NETWORK_INTERFACE = __app_net_configs__["primary_interface"]
    SRC_PATH = __test_configs__["src_path"]
    GATEWAY = __app_net_configs__["gateway"]
    NET_CHECK_INTERVALS = __app_net_configs__["network_check_intervals"] * 60
    NETWORK_TIMEOUT = __app_net_configs__["timeout"]
    NETWORK_MAX_TIMEOUT_RETRIES = __app_net_configs__["max_connection_timeouts"]

    #logging
    LOG_FILE_DIRECTORY = __dev_configs__["log_file_directory"]
    LOG_FILE_NAME = __dev_configs__["log_file_name"]

# api base url, enpoints
class APIRoutes:
    BASE_URL : str = __var_from_env__("API_URL")
    TEST_URL : str = __var_from_env__("API_TEST_URL")
    SINK_DATA : str = __var_from_env__("SINK_DATA")
    SENSOR_DATA : str = __var_from_env__("SENSOR_DATA")
    HEADERS = settings_yaml["headers"]

# api configurations
class APIConfigs:
    SECRET_KEY : str = __var_from_env__("SECRET_KEY")

# mqtt broker configuration
class Broker:
    HOST : str = __var_from_env__("BROKER_HOST_ADDRESS")
    PORT : int = int(__var_from_env__("BROKER_PORT"))
    ROOT_TOPIC : str = __topics_from_env__("ROOT_TOPIC")[0]

# mqtt dev topics
class DevTopics:
    TEST = "/dev/test"

# mqtt functional topics
class Topics:
    SENSOR : List[str] = __topics_from_env__("SENSOR")
    SINK : List[str] = __topics_from_env__("SINK")
    ADMIN : List[str] = __topics_from_env__("ADMIN")

# returns two lists of ** all ** available topics
# one for application topics the other for system topics
def get_topics() -> Tuple[list, list]:
    _topics: List[str] = []

    _topic_lists : List[List] = [Topics.ADMIN, Topics.SINK, Topics.SENSOR]

    # go over each topic list, and then over each topic
    # then insert the root topic before the subtopic
    for _list in _topic_lists:
        for topic in _list:
            _topics.append(f"{Broker.ROOT_TOPIC}{topic}")
    
    # TODO: see what $SYS topics to add for sink node data
    # return this with app_topics when thats done ^
    _sys_topics = ["$SYS/broker/load/bytes/sent", "$SYS/broker/clients/connected"]

    return _topics, []