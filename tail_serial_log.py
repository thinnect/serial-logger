#!/usr/bin/env python2

""" Tail the serial_logger logfiles with color output """

__author__ = "Raido Pahtma"
__license__ = "MIT"

import sys
import os
import time

INTERVAL = 0.1

def color_logger_line(line):
    line = line.lstrip().rstrip()
    if "E|" in line:
        return '\033[91m' + line + '\033[0m'
    if "W|" in line:
        return '\033[93m' + line + '\033[0m'
    if "I|" in line:
        return '\033[97m' + line + '\033[0m'
    return line

def tailfile(file):
    while True:
        where = file.tell()
        line = file.readline()
        if not line:
            time.sleep(INTERVAL)
            file.seek(where)
        else:
            yield color_logger_line(line)

if __name__ == "__main__":

    if len(sys.argv) == 2:
        filename = sys.argv[1]

        try:
            filesize = os.stat(filename)[6]
            file = open(filename, "r")
            file.seek(filesize)

            for line in tailfile(file):
                print line

        except KeyboardInterrupt:
            print "interrupted"
            file.close()
            sys.stdout.flush()
    else:
        print "Specify file to tail!"
        sys.exit(1)
