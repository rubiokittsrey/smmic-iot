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
    _settings_yaml = yaml.safe_load(sfile)
_app_net_configs = _settings_yaml["app_configurations"]["network"] # the application network configurations
_test_configs = _settings_yaml["app_configurations"]["tests"] # testing configurations
_dev_configs = _settings_yaml["dev_configs"]
_hardware_configs = _settings_yaml["hardware_configurations"]

# load the .env variables
_envpath = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(_envpath)

# get variables from the .env file
def _from_env(key: str) -> Any:
    var = os.getenv(key)
    if var:
        return var

# global vars
LOGGING_LEVEL = logging.DEBUG
ENABLE_LOG_TO_FILE =  _dev_configs["enable_log_to_file"]
_DEV_MODE = False

def set_logging_level(level: int) -> None:
    global LOGGING_LEVEL
    LOGGING_LEVEL = level

def enable_log_to_file(value: bool) -> None:
    global ENABLE_LOG_TO_FILE
    ENABLE_LOG_TO_FILE = value

# FIXME: not working properly
# NOTE: supposed to set a global variable _DEV_MODE to true in order to
# inform the operation that it is on development mode
def dev_mode(val: bool) -> None:
    global _DEV_MODE
    _DEV_MODE = val

def __get_dev_mode__() -> bool:
    return _DEV_MODE
DEV_MODE = __get_dev_mode__()

# development configurations
# class DevConfigs:

# application configurations 
class APPConfigurations:
    GLOBAL_SEMAPHORE_COUNT : int = _settings_yaml["app_configurations"]["global_semaphore_count"]

    MQTT_PW : str = _settings_yaml["app_configurations"]["mqtt_pwd"]
    MQTT_USERNAME : str = _settings_yaml["app_configurations"]["mqtt_username"]

    CLIENT_ID : str = _settings_yaml["app_configurations"]["client_id"]
    PRIMARY_NET_INTERFACE : str = _app_net_configs["primary_interface"]
    SRC_PATH : str = _test_configs["src_path"]
    GATEWAY : str = _app_net_configs["gateway"]
    NET_CHECK_INTERVALS = _app_net_configs["network_check_intervals"] * 60
    NETWORK_TIMEOUT : int = _app_net_configs["timeout"]
    NETWORK_MAX_TIMEOUT_RETRIES : int = _app_net_configs["max_connection_timeouts"]
    API_DISCON_WAIT : int = _settings_yaml['app_configurations']['api_disconnect_await']

    # local storage
    LOCAL_STORAGE_DIR : str = _settings_yaml["app_configurations"]["local_storage"]["directory"]

    #logging
    LOG_FILE_DIRECTORY : str = _dev_configs["log_file_directory"]
    LOG_FILE_NAME : str = _dev_configs["log_file_name"]

    @staticmethod
    def _disable_irr() -> bool | None:
        val: bool | None = None
        try:
            val = _settings_yaml["app_configurations"]["disable_irrigation"]
        except KeyError:
            pass
        return val

    DISABLE_IRRIGATION: bool | None = _disable_irr()

    # pysher configurations
    PUSHER_APP_ID : str = _settings_yaml["app_configurations"]["pusher"]["app_id"]
    PUSHER_KEY : str = _settings_yaml["app_configurations"]["pusher"]["key"]
    PUSHER_SECRET : str = _settings_yaml["app_configurations"]["pusher"]["secret"]
    PUSHER_CLUSTER : str = _settings_yaml["app_configurations"]["pusher"]["cluster"]
    PUSHER_SSL : bool = _settings_yaml["app_configurations"]["pusher"]["ssl"]
    PUSHER_CHANNELS : List[str] = _settings_yaml["app_configurations"]["pusher"]["channels"]
    PUSHER_EVENT_IRR : str = _from_env('PUSHER_EVENT_IRRIGATION')
    PUSHER_EVENT_INT : str = _from_env('PUSHER_EVENT_INTERVAL')

# api base url, enpoints
class APIRoutes:
    BASE_URL : str = _from_env('API_URL')
    TEST_URL : str = f"{BASE_URL}{_from_env('API_TEST_URL')}"
    HEADERS : str = _settings_yaml["headers"]
    HEALTH : str = f"{BASE_URL}{_from_env('HEALTH_CHECK_URL')}"

    # sink endpoints
    SINK_DATA : str = f"{BASE_URL}{_from_env('SINK_DATA')}"

    # sensor endpoints
    SENSOR_DATA : str = f"{BASE_URL}{_from_env('SENSOR_DATA')}"
    SENSOR_ALERT : str = f"{BASE_URL}{_from_env('SENSOR_ALERT')}"

# api configurations
class APIConfigs:
    SECRET_KEY : str = _from_env("SECRET_KEY")

# mqtt broker configuration
class Broker:
    HOST : str = _from_env("BROKER_HOST_ADDRESS")
    PORT : int = int(_from_env("BROKER_PORT"))
    ROOT_TOPIC : str = _from_env("ROOT_TOPIC")

# mqtt dev topics
class DevTopics:
    TEST = "/dev/test"

class Channels:
    IRRIGATION = _hardware_configs["irrigation_channel"]

# mqtt functional topics
class Topics:
    ROOT_TOPIC : str = _from_env("ROOT_TOPIC")
    ADMIN_SETTINGS : str = f"{ROOT_TOPIC}{_from_env('ADMIN_SETTINGS_TOPIC')}"
    ADMIN_COMMANDS : str = f"{ROOT_TOPIC}{_from_env('ADMIN_COMMANDS_TOPIC')}"
    SENSOR_DATA : str = f"{ROOT_TOPIC}{_from_env('SENSOR_DATA_TOPIC')}"
    SENSOR_ALERT : str = f"{ROOT_TOPIC}{_from_env('SENSOR_ALERT_TOPIC')}"
    SINK_DATA : str = f"{ROOT_TOPIC}{_from_env('SINK_DATA_TOPIC')}"
    SINK_ALERT : str = f"{ROOT_TOPIC}{_from_env('SINK_ALERT_TOPIC')}"
    IRRIGATION : str = f"{ROOT_TOPIC}{_from_env('IRRIGATION_TOPIC')}"

    # command / trigger topics
    SE_INTERVAL_TRIGGER : str = f"{ROOT_TOPIC}{_from_env('SENSOR_INTERVAL_TRIGGER')}"
    SE_IRRIGATION_TRIGGER : str = f"{ROOT_TOPIC}{_from_env('SENSOR_IRRIGATION_TRIGGER')}"

    # sys topics
    SYS_BYTES_RECEIVED : str = _from_env('BROKER_BYTES_RECEIVED')
    SYS_BYTES_SENT : str = _from_env('BROKER_BYTES_SENT')
    SYS_CLIENTS_CONNECTED : str = _from_env('BROKER_CLIENTS_CONNECTED')
    SYS_CLIENTS_TOTAL : str = _from_env('BROKER_CLIENTS_TOTAL')
    SYS_MESSAGES_RECEIVED : str = _from_env('BROKER_MESSAGES_RECEIVED')
    SYS_MESSAGES_SENT : str = _from_env('BROKER_MESSAGES_SENT')
    SYS_SUB_COUNT : str = _from_env('BROKER_SUBSCRIPTIONS_COUNT')

    @staticmethod
    def get_topics() -> Tuple[List[str], List[str]]:
        smmic_topics: List[str] = []
        sys_topics: List[str] = []

        for key, value in vars(Topics).items():
            if not value or type(value) != str:
                continue
            if not key.startswith("__"):
                topic_value = getattr(Topics, key)
                if key.startswith("SYS"):
                    sys_topics.append(topic_value)
                else:
                    smmic_topics.append(topic_value)

        return smmic_topics, sys_topics
                    

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

class Registry:

    class Triggers:

        class contexts:
            API_CONNECTION_STATUS = 'api_connection_status'
            UNSYNCED_DATA = 'unsynced_data'
            
            # commands
            SE_INTERVAL = "se_interval"
            SE_IRRIGATION_OVERRIDE = "se_irrigation_override"

    class Modules:
        
        # ----- common -----
        
        class Settings:
            alias = 'settings'

        class Utils:
            alias = 'utils'

        # ----- main -----

        class Main:
            alias = 'smmic'

        class TaskManager:
            alias = 'task-manager'

        # ----- data -----

        class LocalStorage:
            alias = 'locstorage'
            origin_unsynced = 'locstorage_unsynced'

        class HttpClient:
            alias = 'http-client'

        class Requests:
            alias = 'requests'

        class SystemMonitor:
            alias = 'sysmonitor'

        class PysherClient:
            alias = 'pysher-client'

        # ----- mqtt -----

        class MqttClient:
            alias = 'mqtt-client'

        class Service:
            alias = 'service'

        class telemetrymanager:
            alais = 'telemetry-manager'
        
        # ----- hardware -----

        class Hardware:
            alias = 'hardware'

        class Network:
            alias = 'network'

        class Irrigation:
            alias = 'irrigation'