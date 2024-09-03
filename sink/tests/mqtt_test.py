# mqtt module unit tests

# third-party
import argparse
import sys
import logging
import time
import os
import asyncio

# internal
try:
    sys.path.append('/mnt/d/projects/smmic-iot/sink/common')
except Exception as e:
    print(f'Exception raised: {e}')
    os._exit(0)

import settings
sys.path.append(settings.APPConfigurations.SRC_PATH)
import mqtt.client as client
import mqtt.service as service
from utils import Modes, log_config, status
import pub
import sub

__log__ = log_config(logging.getLogger(__name__))

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

    client_funcs = [
        "start_callback_client",
        "subscribe"
    ]

    for func in client_funcs:
        client_subparser.add_parser(func, help=f"Test the {func} function of the client module")


    # parse arguments
    args = parser.parse_args()

    if not args.module:                              
        parser.print_help()
        parser_service.print_help()
        parser_client.print_help()

    # service module unit tests
    elif args.module == "service":
        if not args.function or args.function == "status_check":
            service.mqtt_status_check()

    # client module unit tests
    elif args.module == "client":

        # test the get_client function of the mqtt app
        # expected output:
        # --- function returns nothing, initiates the callback client, connects and starts the loop using asyncio
        # publishes a message on /dev/test topic
        # receives messages from *all* other topics
        if args.function == "start_callback_client":
            async def start_c_pub_task():
                while True:
                    if client.CALLBACK_CLIENT:
                        client.CALLBACK_CLIENT.message_callback_add("#", sub.callback_mqtt_test)
                        if client.CLIENT_STAT == status.CONNECTED:
                            try:
                                pub.publish(client.CALLBACK_CLIENT, settings.DevTopics.TEST)
                            except Exception as e:
                                __log__.error(f'Callback client from client module was unable to published message to topic: {settings.DevTopics.TEST} ({e})')
                            except asyncio.CancelledError:
                                __log__.warning(f'raised KeyboardInterrupt, cancelling mqtt_test.start_c_pub_task() at PID at PID {os.getpid()}')
                        elif client.CLIENT_STAT == status.FAILED: 
                            # TODO: fix this condition (idea: implement queues?)
                            __log__.error(f'SMMIC callback client status failed, terminating mqtt_test.start_c_pub_task() at {os.getpid()}')
                            break
                        else:
                            __log__.warning(f'Unable to publish message to topic: {settings.DevTopics.TEST} (client not connected)')
                    await asyncio.sleep(5)
                    
            async def start_c_client_test():
                #TODO: when this thread is terminated with KeyboardInterrupt, it throws a trace error
                __log__.debug(f'Running mqtt_test.start_callback_client() at PID: {os.getpid()}')
                c_cli = asyncio.create_task(client.start_callback_client())
                pub_task = asyncio.create_task(start_c_pub_task())
                task_list = [c_cli, pub_task]
                try:
                    await asyncio.gather(*task_list)
                except asyncio.CancelledError:
                    __log__.warning(f'raised KeyboardInterrupt, cancelling mqtt_test.start_call_client() at PID: {os.getpid()}')
                    await asyncio.gather(client.__shutdown_disconnect__())
                
            asyncio.run(start_c_client_test())

        # test the subscribe function of the mqtt app
        if args.function == "subscribe":
            client.__subscribe__(client=None)