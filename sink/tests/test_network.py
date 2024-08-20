import sys
import os
import settings

sys.path.append(settings.APPConfigurations.SRC_PATH)

from hardware import network
import argparse

# debugging
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test network.py. Will run monitor_network() if no arguments are passed")

    subparser = parser.add_subparsers(dest='function')

    parser_monitor_network = subparser.add_parser("network_monitor", help="Monitor network connectivity")

    parser_ping = subparser.add_parser("ping", help="Ping an host")
    parser_ping.add_argument("--host", help="The host to ping")
    parser_ping.add_argument("--repeat", type=int, help="Repeat the ping n amount of times (default: 1)")

    parser_check_interface = subparser.add_parser("check_interface", help="Check available interfaces. Ignores the localhost interface")

    parser_timeout_handler = subparser.add_parser("timeout_handler", help="Test the timeout handler. Forces timeout of all processes if a critical network check (i.e. check_interface) fails")

    parser_init_network = subparser.add_parser("init_network", help="Test the init network function of the network module")
    parser_init_network.add_argument("--func", help="The function to pass to timeout handler")

    args = parser.parse_args()

    if(not args.function or args.function == 'network_monitor'):
        network.network_monitor()
    elif(args.function == 'ping'):
        network.__ping__(host=args.host, repeat=args.repeat if args.repeat else 1)
    elif(args.function == 'check_interface'):
        network.__check_interface__()
    elif(args.function == 'timeout_handler'):
        network.__time_out_handler__(network.__ping__)