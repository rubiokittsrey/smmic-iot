import sys

sys.path.append('/mnt/d/projects/smmic-iot/sink/common')

import settings

sys.path.append(settings.APPConfigurations.SRC_PATH)

import logging
        
from hardware import network
from utils import Modes, log_config
import argparse

# debugging
if __name__ == "__main__":
    # tests should start in dev mode
    Modes.dev()
    
    parser = argparse.ArgumentParser(description="Test network.py. Will run monitor_network() by default if no arguments are passed")
    subparser = parser.add_subparsers(dest='function')

    # test the network check function
    parser_network_check = subparser.add_parser("network_check", help="Check network connectivity")

    # test the ping function with arguments
    parser_ping = subparser.add_parser("ping", help="Ping an host")
    parser_ping.add_argument("--host", help="The host to ping")
    parser_ping.add_argument("--repeat", type=int, help="Repeat the ping n amount of times (default: 1)")

    # test the check interface function
    parser_check_interface = subparser.add_parser("check_interface", help="Check available interfaces. Ignores the localhost interface")

    # test the timeout handler function
    # NOTE: this function is currently still not implemented properly and is not directly involved in any processes involving the network module
    parser_timeout_handler = subparser.add_parser("timeout_handler", help="Test the timeout handler. Forces timeout of all processes if a critical network check (i.e. check_interface) fails")

    args = parser.parse_args()

    if(not args.function or args.function == 'network_check'):
        network.network_check()
    elif(args.function == 'ping'):
        network.__ping__(host=args.host, repeat=args.repeat if args.repeat else 1)
    elif(args.function == 'check_interface'):
        network.__check_interface__()
    elif(args.function == 'timeout_handler'):
        network.__time_out_handler__(network.__ping__)