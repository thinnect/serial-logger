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


class HdlcParser:
    def __init__(self, timeout=0.2):
        self.timestamp = time.time()
        self.timeout = timeout
        self.buf = ""

    def put(self, data):
        if data:
            self.timestamp = time.time()
            self.buf += data

    def __iter__(self):
        return self

    def next(self):
        if len(self.buf) > 2:
            delim = self.buf[1:].find("\x7e")
            if delim == -1:
                if time.time() - self.timestamp > self.timeout:
                    t = self.buf
                    self.buf = ""
                    return self.timestamp, t.encode("hex").upper(), False
                else:
                    raise StopIteration
            else:
                t = self.buf[:delim+2]
                self.buf = self.buf[delim+2:]
                return self.timestamp, t.encode("hex").upper(), True
        else:
            raise StopIteration


class SerialLogger(object):

    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.serial_timeout = 0.01 if sys.platform == "win32" else 0

    def run(self):
        print "Using  %s:%u" % (self.port, self.baud)

        while True:
            parser = HdlcParser()
            serialport = None

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

    logger = SerialLogger(args.port, args.baud)
    logger.run()
