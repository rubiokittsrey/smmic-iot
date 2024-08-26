# the main python script managing all scripts within /src directory

# other packages
import logging
import argparse
import paho.mqtt.client as mqtt

# modules from packages in smmic
from src.hardware import network
from src.mqtt import service, client
import os
import asyncio
import time

# smmic commons
from utils import log_config, set_logging_configuration, Modes, status
from settings import Broker

log = log_config(logging.getLogger(__name__))

def test_callback(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    log.info(f'Test topic ({msg.topic}) payload: {str(msg.payload.decode('utf-8'))}')

# initialize system, perform checks
def init():
    # network check, check interfaces, ping gateway
    net_check = network.network_check()
    if not net_check:
        log.critical(f'Network check returned with errors, terminating main process now')
        #TODO: handle no internet connection scenario
    else:
        log.info(f'Network check successful, proceeding under normal operating conditions')

    # mosquitto service check
    # terminate program if mosquitto_service_check() returns INACTIVE or FAILED status
    mqtt_status = service.mqtt_status_check()
    if mqtt_status == status.INACTIVE or mqtt_status == status.FAILED:
        os._exit(0)

    # client initialization
    callback_client = client.client()
    callback_client.message_callback_add("/dev/test", test_callback)

    #TODO: implement proper loop for callback function using concurrency
    callback_client.loop_start()
    while True:
        if not client.CONNECTED:
            log.info(f'Attempting connection with broker at {Broker.HOST}:{Broker.PORT}')
            time.sleep(5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The main module of the SMMIC application for the Raspberry Pi 4")
    subparser = parser.add_subparsers(dest='command')

    # subparsers
    start = subparser.add_parser('start', help='Start the SMMIC MQTT application.')

    # start subparser parsers
    start_subparser = start.add_subparsers(dest='mode', help='Set the application mode. The default mode sets the logging level to WARNING with logging to file enabled.')
    dev = start_subparser.add_parser('dev', help='Start the application in development mode using verbose logging to terminal and with logging to file disabled.')
    normal = start_subparser.add_parser('normal', help='Start the application in normal mode with \'warning\' level logging.')
    info = start_subparser.add_parser('info', help='Start the application in info mode with \'info\' level logging')
    debug = start_subparser.add_parser('debug', help='Start the application in debug mode, uses verbose logging.')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        start.print_help()
    elif args.command == 'start':
        if not args.mode:
            start.print_help()
        elif args.mode == 'dev':
            Modes.dev()
            log.info('Starting in development mode - VERBOSE logging enabled, logging to file disabled')
        elif args.mode == 'normal' or not args.mode:
            log.info('Starting in normal mode with WARNING level logging and logging to file enabled')
            Modes.normal()
        elif args.mode == 'info':
            log.info('Starting in normal mode with INFO level logging and logging to file enabled')
            Modes.info()
        elif args.mode == 'debug':
            log.info('Starting in debug mode with DEBUG level logging and logging to file enabled')
            Modes.debug()

        init()