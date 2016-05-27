#!/usr/bin/env python2
"""tail_serial_log.py: Tail the serial_logger logfiles with color output """

import sys
import os
import time

from .mote_serial_logger import color_logger_line


__author__ = "Raido Pahtma"
__license__ = "MIT"


def tail_file(file, interval=0.1):
    while True:
        where = file.tell()
        line = file.readline()
        if not line:
            time.sleep(interval)
            file.seek(where)
        else:
            yield color_logger_line(line)


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Serial logger")
    parser.add_argument("file", default="/dev/ttyUSB0", nargs='?')
    parser.add_argument("--interval", type=float, default=0.1)
    args = parser.parse_args()

    try:
        size = os.stat(args.file)[6]
        file = open(args.file, "r")
    except Exception as e:
        print("Exception {:s}".format(e))
        sys.exit(1)

    try:
        file.seek(size)
        for line in tail_file(file, interval=args.interval):
            print(line)

    except KeyboardInterrupt:
        print("interrupted")
        file.close()
        sys.stdout.flush()


if __name__ == "__main__":
    main()
