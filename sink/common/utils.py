import logging as __logging__
import settings

def pretty_print(message, ):
    print(f'')

#TODO: ENABLE WRITING TO LOG FILE!!

class logs:
    if(not settings.DevConfigs.ENABLE_LOG_TO_FILE):
        print('Logging to file disabled')
    def error(message):
        print(f'\033[31m{message}\033[0m')
    def warning(message):
        print(f'\33[33m{message}\033[0m')
    def success(message):
        print(f'\033[32m{message}\033[0m')
    def info(message):
        print(f'\033[0m{message}\033[0m')