#!/usr/bin/env python2

""" Serial port logger """

__author__ = "Raido Pahtma"
__license__ = "MIT"

import os
import sys
import serial
import time
import datetime


def log_timestr(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:23]


class LineParser(object):

    def __init__(self, delimiter="\x7e", include_delimiter=True, timeout=0.2):
        self.timestamp = time.time()
        self.delimiter = delimiter
        self.include_delimiter = include_delimiter
        self.timeout = timeout
        self.buf = ""
        self.lines = []

    def clear(self):
        self.buf = ""
        self.lines = []

    def put(self, data):
        if data:
            timestamp = time.time()

            if self.buf == "":
                self.timestamp = timestamp

            self.buf += data
            while len(self.buf) > 1:
                delim = self.buf[1:].find(self.delimiter)
                if delim == -1:
                    break
                else:
                    t = self.buf[:delim+2]
                    self.buf = self.buf[delim+2:]
                    if not self.include_delimiter:
                        t = t.rstrip(self.delimiter).lstrip(self.delimiter)
                    self.lines.append((self.timestamp, t.encode("hex").upper()))
                    self.timestamp = timestamp

    def __iter__(self):
        return self

    def next(self):
        if len(self.lines) > 0:
            timestamp, line = self.lines.pop(0)
            return timestamp, line, True
        else:
            if self.buf and time.time() - self.timestamp > self.timeout:
                t = self.buf
                if not self.include_delimiter:
                    t = t.rstrip(self.delimiter).lstrip(self.delimiter)
                self.buf = ""
                return self.timestamp, t.encode("hex").upper(), False

        raise StopIteration

class SerialLogger(object):

    def __init__(self, port, baud, parser):
        self.port = port
        self.baud = baud
        self.serial_timeout = 0.01 if sys.platform == "win32" else 0

    def run(self):
        print "Using  %s:%u" % (self.port, self.baud)

        while True:
            serialport = None
            parser.clear()

            try:
                while serialport is None:
                    try:
                        serialport = serial.Serial(self.port, self.baud, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=self.serial_timeout, xonxoff=0, rtscts=0)
                        serialport.flushInput()
                    except (serial.SerialException, OSError):
                        serialport = None
                        time.sleep(0.1)

                print "Opened %s:%u" % (self.port, self.baud)

                try:
                    while True:
                        parser.put(serialport.read(1000))

                        for timestamp, line, complete in parser:
                            print "%s : %s%s" % (log_timestr(timestamp), line, "" if complete else " ...")
                            sys.stdout.flush()

                        time.sleep(0.01)

                except serial.SerialException as e:
                    print "Disconnected: %s, will try to open again ..." % (e.message)

            except KeyboardInterrupt:
                if serialport is not None and serialport.isOpen():
                    serialport.close()
                    print
                    print "Closed %s:%u" % (self.port, self.baud)
                break


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Serial logger")
    parser.add_argument("port", default="/dev/ttyUSB0")
    parser.add_argument("baud", default=115200, type=int)
    args = parser.parse_args()

    parser = LineParser()
    logger = SerialLogger(args.port, args.baud, parser)
    logger.run()
