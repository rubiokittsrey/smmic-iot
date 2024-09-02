# this module contains the project settings, configurations, constants, all loaded from configs.yaml
# configs.yaml is gitignored by default
import os
import yaml
import logging
from typing import Tuple

spath = os.path.join(os.path.dirname(__file__), '../settings.yaml')

with open(spath, 'r') as sfile:
    settings_yaml = yaml.safe_load(sfile)

__app_net_configs__ = settings_yaml["app_configurations"]["network"]
__test_configs__ = settings_yaml["app_configurations"]["tests"]
__base_url__ = settings_yaml["api_routes"]["base_url"]
__api_endpoints__ = settings_yaml["api_routes"]["endpoints"]
__api_configs__ = settings_yaml["api_configurations"]
__broker_configs__ = settings_yaml["broker"]
__dev_configs__ = settings_yaml["dev_configs"]
__smmic_topics__ = settings_yaml["topics"]

LOGGING_LEVEL = logging.DEBUG
ENABLE_LOG_TO_FILE =  __dev_configs__["enable_log_to_file"]

def set_logging_level(level):
    global LOGGING_LEVEL
    LOGGING_LEVEL = level

def enable_log_to_file(value):
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
    NETWORK_MAX_TIMEOUTS = __app_net_configs__["max_connection_timeouts"]

    #logging
    LOG_FILE_DIRECTORY = __dev_configs__["log_file_directory"]
    LOG_FILE_NAME = __dev_configs__["log_file_name"]

# api base url, enpoints
class APIRoutes:
    BASE_URL = __base_url__
    TEST_URL = __api_endpoints__["rpi_test"]
    HEADERS = settings_yaml["headers"]

# api configurations
class APIConfigs:
    SECRET_KEY = __api_configs__["secret_key"]

# mqtt broker configuration
class Broker:
    HOST = __broker_configs__["host"]
    PORT = __broker_configs__["port"]
    ROOT_TOPIC = __broker_configs__["root_topic"]

# mqtt dev topics
class DevTopics:
    TEST = "/dev/test"

# mqtt functional topics
class SensorTopics:
    #BROADCAST = "/broadcast"
    DATA = f"{__broker_configs__["root_topic"]}{__smmic_topics__["sensor"]["data"]}"
    ALERT = f"{__broker_configs__["root_topic"]}{__smmic_topics__["sensor"]["alert"]}"

class SinkTopics:
    ALERT = f"{__broker_configs__["root_topic"]}{__smmic_topics__["sink"]["alert"]}"

class AdminTopics:
    SETTINGS = f"{__broker_configs__["root_topic"]}{__smmic_topics__["admin"]["settings"]}" # smmic/admin/settings/[SINK or SENSOR]/[DEVICE ID]
    # COMMANDS = f"{__broker_configs__["root_topic"]}{__smmic_topics__["admin"]["commands"]}" #TODO: IMPLEMENT COMMANDS

# returns two lists of ** all ** available topics
# one for application topics the other for system topics
def get_topics() -> Tuple[list, list]:
    app_topics = [DevTopics.TEST, SensorTopics.DATA, SensorTopics.ALERT, SinkTopics.ALERT, AdminTopics.SETTINGS]
    
    # TODO: see what $SYS topics to add for sink node data
    # return this with app_topics when thats done ^
    sys_topics = ["$SYS/broker/load/bytes/sent", "$SYS/broker/clients/connected"]

    return app_topics, []