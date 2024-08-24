# this module contains the project settings, configurations, constants, all loaded from configs.yaml
# configs.yaml is gitignored by default
import os
import yaml

spath = os.path.join(os.path.dirname(__file__), '../settings.yaml')

with open(spath, 'r') as sfile:
    settings = yaml.safe_load(sfile)

__app_net_configs__ = settings["app_configurations"]["network"]
__test_configs__ = settings["app_configurations"]["tests"]
__base_url__ = settings["api_routes"]["base_url"]
__api_endpoints__ = settings["api_routes"]["endpoints"]
__api_configs__ = settings["api_configurations"]
__broker_configs__ = settings["broker"]
__dev_configs__ = settings["dev_configs"]

class status:
    INFO = 100
    SUCCESS = 200
    ERROR = 400
    WARNING = 300
    CRITICAL = 500
    ACTIVE = SUCCESS
    INACTIVE = WARNING
    FAILED = ERROR

# development configurations
class DevConfigs:
    ENABLE_LOG_TO_FILE =  __dev_configs__["enable_log_to_file"]

# application configurations
class APPConfigurations:
    NETWORK_INTERFACE = __app_net_configs__["primary_interface"]
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
    ROOT_TOPIC = __broker_configs__["root_topic"]

# mqtt dev topics
class DevTopics:
    TEST = "/dev/test"

# mqtt functional topics
class SensorTopics:
    #BROADCAST = "/broadcast"
    DATA = f"{__broker_configs__["root_topic"]}/sensor/+/data"
    ALERT = f"{__broker_configs__["root_topic"]}/sensor/+/alert"

class SinkTopics:
    ALERT = f"{__broker_configs__["root_topic"]}/sink/alert"

class AdminTopics:
    SETTINGS = f"{__broker_configs__["root_topic"]}/admin/settings/#" # smmic/admin/settings/[SINK or SENSOR]/[DEVICE ID]
    COMMANDS = f"{__broker_configs__["root_topic"]}/admin/commands"