import logging as __logging__
import settings
import os
import re

# do not use
def pretty_print(message, ):
    print(f'')

def __init_logs_handlers__(log_path, log_to_file = True): 
    logs_handler = __logging__.FileHandler(log_path)
    console_handler = __logging__.StreamHandler()

    # console_handler.setLevel(__logging__.DEBUG)
    # logs_handler.setLevel(__logging__.DEBUG)

    formatter = __logging__.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    logs_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    return logs_handler, console_handler

# returns the logger object from caller with fromatter, console handler and file handler
def log_config(logger):
    logger.setLevel(__logging__.INFO)
    log_directory = '/home/rubiokittsrey/Projects/smmic-iot/sink/common/logs/'
    log_file = 'smmic.log'
    os.makedirs(log_directory, exist_ok=True)
    log_path = os.path.join(log_directory, log_file)

    logs_handler, console_handler = __init_logs_handlers__(log_path)
    logger.addHandler(logs_handler) if settings.DevConfigs.ENABLE_LOG_TO_FILE else None
    logger.addHandler(console_handler)

    return logger

# parses and returns the ip address, packet loss, and rtt min, avg, max and mdev from a ping output
# just for pretty ping logs, really
def parse_ping(output):
    output_decoded = output.decode('utf-8')

    # patterns
    ip = re.compile(r'PING (\d+\.\d+\.\d+\.\d+)')
    packet_stats = re.compile(r'(\d+) packets transmitted, (\d+) received')
    packet_loss = re.compile(r'(\d+)% packet loss')
    rtt = re.compile(r'rtt min/avg/max/mdev = ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms')

    ip_match = ip.search(output_decoded)
    packet_stats_match = packet_stats.search(output_decoded)
    packet_loss_match = packet_loss.search(output_decoded)
    rtt_match = rtt.search(output_decoded)

    # parsed data
    ip = ip_match.group(1) if ip_match else None
    packet_sent = packet_stats_match.group(1) if packet_stats_match else None
    packet_recieved = packet_stats_match.group(2) if packet_stats_match else None
    packet_loss = packet_loss_match.group(1) if packet_loss_match else None
    rtt_min = rtt_match.group(1) if rtt_match else None
    rtt_avg = rtt_match.group(2) if rtt_match else None
    rtt_max = rtt_match.group(3) if rtt_match else None
    rtt_mdev = rtt_match.group(4) if rtt_match else None

    return ip, packet_sent, packet_recieved, packet_loss, rtt_min, rtt_avg, rtt_max, rtt_mdev