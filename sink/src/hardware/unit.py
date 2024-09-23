# the hardware check for the current unit (computer) that this program is running on
# TODO: documentation

# third-party
import subprocess
import psutil
import time
import logging
from typing import List, Any, Tuple

# internal helpers, configurations
from utils import log_config, is_num
from settings import APPConfigurations

__log__ = log_config(logging.getLogger(__name__))

# returns the total available memory (in kilobytes) of the device
def __mem_check__() -> Tuple[List[int|float], List[int|float]]:
    mem_f : List[int | float] = []
    swap_f : List[int | float] = []

    try:
        # get output of free, decode and then split each newline
        # 
        output = subprocess.check_output(["free"])
        decoded = output.decode('utf-8')
        s_output = decoded.split("\n")

        # the mem and swap out as lists
        # assign to cache as Tuples with the final mem and swap lists
        mem_split : List[Any] = s_output[1].split(' ')
        swap_split: List[Any] = s_output[2].split(' ')
        cache = [(mem_split, mem_f), (swap_split, swap_f)]
        
        # remove any empty occurence within each split
        # and pop the first items 'Mem:' or 'Swap:'
        for split, f in cache:
            for i in range(split.count(' ')):
                split.remove('')

        # the final mem and swap output list
        # contains num values (int / float)
        # convert each content of list to num and append to mem_f
        # then return mem_f [total, used, free, shared, buff/cache, available]
        # see output of 'free': https://www.turing.com/kb/how-to-use-the-linux-free-command
        for split, f in cache:
            for item in split:
                _t = is_num(item)
                if not _t:
                    pass
                else:
                    f.append(_t(item))

    except Exception as e:
        __log__.error(f"Unhandled exception occured at unit.__mem_check__: {str(e)}")

    return mem_f, swap_f

if __name__ == '__main__':
    mem, swap = __mem_check__()