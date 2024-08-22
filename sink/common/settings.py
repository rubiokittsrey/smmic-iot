# this module contains the project settings, configurations, constants, all loaded from configs.yaml
# configs.yaml is gitignored by default
import os
import yaml

spath = os.path.join(os.path.dirname(__file__), '../settings.yaml')

with open(spath, 'r') as sfile:
    settings = yaml.safe_load(sfile)

__app_net_configs__ = settings["app_configurations"]["network"]
__test_configs__ = settings["app_configurations"]["tests"]
__dev_topics__ = settings["mqtt_topics_dev"]
__base_url__ = settings["api_routes"]["base_url"]
__api_endpoints__ = settings["api_routes"]["endpoints"]
__api_configs__ = settings["api_configurations"]
__broker_configs__ = settings["mqtt_broker"]
__topics__ = settings["mqtt_topics_smmic"]
__dev_configs__ = settings["dev_configurations"]

# development configurations
class DevConfigs:
    ENABLE_LOG_TO_FILE =  __dev_configs__["enable_log_to_file"]

# application configurations
class APPConfigurations:
    SRC_PATH = __test_configs__["src_path"]
    GATEWAY = __app_net_configs__["gateway"]
    NET_CHECK_INTERVALS = __app_net_configs__["network_check_intervals"] * 60
    NETWORK_TIMEOUT = __app_net_configs__["timeout"]
    NETWORK_MAX_TIMEOUTS = __app_net_configs__["max_connection_timeouts"]

# api base url, enpoints
class APIRoutes:
    BASE_URL = __base_url__
    TEST_URL = __api_endpoints__["rpi_test"]
    HEADERS = settings["headers"]

# api configurations
class APIConfigs:
    SECRET_KEY = __api_configs__["secret_key"]

# mqtt broker configuration
class Broker:
    HOST = __broker_configs__["host"]
    PORT = __broker_configs__["port"]

# mqtt dev topics
class DevTopics:
    TEST = __dev_topics__["test"]
    SENSOR_ONE = __dev_topics__["sensor1"]
    SENSOR_TWO = __dev_topics__["sensor2"]

# mqtt functional topics
class Topics:
    BROADCAST = __topics__["broadcast"]