# the main python script managing all scripts within /src directory
import logging
import argparse

# TESTING IMPORTS BELOW
from src.hardware import network
import src.api as api
from utils import log_config, set_logging_configuration
import settings

log = log_config(logging.getLogger(__name__))

def init():
    net_check = network.network_check()
    if not net_check:
        log.critical(f'Network check returned with errors, terminating main process now')
    else:
        log.info(f'Network check successful, proceeding with normal operation')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The main module of the SMMIC application for the Raspberry Pi 4")

    subparser = parser.add_subparsers(dest='command')

    start = subparser.add_parser('start', help='Start the SMMIC MQTT application.')

    # start subparsers
    start_subparser = start.add_subparsers(dest='mode', help='Set the application mode. The default mode sets the logging level to WARNING with logging to file enabled.')
    dev = start_subparser.add_parser('dev', help='Start the application in development mode using verbose logging to terminal and with logging to file disabled.')
    normal = start_subparser.add_parser('normal', help='Start the application in normal mode with \'warning\' level logging.')
    info = start_subparser.add_parser('info', help='Start the application in info mode with \'info\' level logging')
    debug = start_subparser.add_parser('debug', help='Start the application in debug mode, uses verbose logging.')

    args = parser.parse_args()

    if not args.command or args.command == 'start':

        if args.mode == 'dev':
            log.info('Starting application in development mode - VERBOSE logging enabled, logging to file disabled')
            settings.set_logging_level(logging.DEBUG)
            settings.enable_log_to_file(False)
            set_logging_configuration()

        if args.mode == 'normal' or args.mode == None:
            log.info('Starting application in normal mode with WARNING level logging')
            settings.set_logging_level(logging.INFO)
            settings.set_logging_level(logging.WARNING)

        if args.mode == 'info':
            log.info('Starting application in normal mode with INFO level logging')
            settings.set_logging_level(logging.INFO)
            set_logging_configuration()

        if args.mode == 'debug':
            log.info('Starting the applicaiton in debug mode with DEBUG level logging')
            settings.set_logging_level(logging.DEBUG)
            set_logging_configuration()

        init()