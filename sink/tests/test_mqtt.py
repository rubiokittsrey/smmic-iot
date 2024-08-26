import sys
import settings

sys.path.append(settings.APPConfigurations.SRC_PATH)

from mqtt import service
from utils import Modes
import argparse

# debugging
if __name__ == "__main__":
    Modes.dev()

    parser = argparse.ArgumentParser(description="Test the mqtt modules")
    subparser = parser.add_subparsers(dest="function")

    # test mqtt status check function
    parser_stat_check = subparser.add_parser("status_check", help="Check mosquitto.service broker status and verify the port the service is listening on")

    # parse arguments
    args = parser.parse_args()

    if args.function == 'status_check':
        service.mqtt_status_check()