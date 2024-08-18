# this module contains the project settings, configurations, constants, all loaded from configs.yaml
# configs.yaml is gitignored by default

import os
import yaml

config_path = os.path.join(os.path.dirname(__file__), '../settings.yaml')

with open(config_path, 'r') as config_file:
    config = yaml.safe_load(config_file)

# api base url, endpoints
class APIRoutes:
    BASE_URL = config["base_url"]
    TEST_URL = config['base_url'] + config['endpoints']['rpi_test']
    HEADERS = config["headers"]

# api configurations
class APIConfigs:
    SECRET_KEY = config['api_configurations']['secret_key']

# mqtt broker configurations
class MQTTBroker:
    HOST = config["mqtt_broker"]["host"]
    PORT = config["mqtt_broker"]["port"]

# mqtt dev topics
class MQTTDevTopics:
    TEST = config["mqtt_topics_dev"]["test"]

# mqtt functional topics
class SMMICTopics:
    BROADCAST = config["mqtt_topics_smmic"]["broadcast"]