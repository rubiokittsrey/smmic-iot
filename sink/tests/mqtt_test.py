# mqtt module unit tests
import sys
import settings

sys.path.append(settings.APPConfigurations.SRC_PATH)

import mqtt.client as client
import mqtt.service as service
from utils import Modes
import argparse

# terminal debugging
if __name__ == "__main__":
    Modes.dev()

    parser = argparse.ArgumentParser(description="Test the mqtt modules")
    subparser = parser.add_subparsers(dest="module")

    # mqtt module parsers
    parser_service = subparser.add_parser("service", help="Test the service module")
    parser_client = subparser.add_parser("client", help="Test the client module")

    # service subparser parsers
    service_subparser = parser_service.add_subparsers(dest="function")
    status_check = service_subparser.add_parser("status_check", help="Test the status check function of the service module")

    # client module parsers
    client_subparser = parser_client.add_subparsers(dest="function")
    client_func = client_subparser.add_parser("get_client", help="Test the client function of the client module")

    # parse arguments
    args = parser.parse_args()

    if not args.module:                              
        parser.print_help()
        parser_service.print_help()
        parser_client.print_help()
    elif args.module == "service":
        if not args.function or args.function == "status_check":
            service.mqtt_status_check()
    elif args.module == "client":
        if args.function == "get_client":
            callback = client.get_client()
            #TODO: handle connection testing with the callback client