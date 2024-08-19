import sys
import os

sys.path.append('/home/rubiokittsrey/Projects/smmic-iot/sink/src/')

from hardware import network
import argparse

# debugging
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test network.py. Will run monitor_network() if no arguments are passed")

    subparser = parser.add_subparsers(dest='function')

    parser_monitor_network = subparser.add_parser("monitor_network", help="Monitor network connectivity")

    parser_ping = subparser.add_parser("ping", help="Ping an host")
    parser_ping.add_argument("--host", help="The host to ping")
    parser_ping.add_argument("--repeat", type=int, help="Repeat the ping n amount of times (default: 1)")

    parser_check_interface = subparser.add_parser("check_interface", help="Check available interfaces. Ignores the localhost interface")

    args = parser.parse_args()

    if(not args.function or args.function == 'monitor_network'):
        network.monitor_network()
    elif(args.function == 'ping'):
        network.__ping__(host=args.host, repeat=args.repeat)
    elif(args.function == 'check_interface'):
        network.__check_interface__()