import logging as __logging__

def pretty_print(message, ):
    print(f'')

class logs:
    def error(message):
        print(f'\033[31m{message}\033[0m')
    def warning(message):
        print(f'\33[33m ● {message}\033[0m')
    def success(message):
        print(f'\033[32m ✓ {message}\033[0m')
    def info(message):
        print(f'\033[0m ✓ {message}\033[0m')