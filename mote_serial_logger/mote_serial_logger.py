#!/usr/bin/env python2
"""serial_logger.py: Serial port logger."""

import os
import sys
import time
import datetime

import serial


__author__ = "Raido Pahtma"
__license__ = "MIT"


version = "0.2.0"


def log_time_str(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:23]


def nocolor_logger_line(line):
    return line


def color_logger_line(line):
    line = line.lstrip().rstrip()
    if line.startswith("E|"):
        return '\033[91m' + line + '\033[0m'
    if line.startswith("W|"):
        return '\033[93m' + line + '\033[0m'
    if line.startswith("I|"):
        return '\033[97m' + line + '\033[0m'
    return line


def encode_hex_line(line):
    return line.encode("hex").upper()


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
                    self.lines.append((self.timestamp, t))
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
                return self.timestamp, t, False

        raise StopIteration


class SerialLogger(object):

    def __init__(self, port, baud, parser, encoder, logfile):
        self.port = port
        self.baud = baud
        self.parser = parser
        self.encoder = encoder
        self.serial_timeout = 0.01 if sys.platform == "win32" else 0
        self.logfile = logfile

    def run(self):
        while True:
            sp = None
            self.parser.clear()

            try:
                while sp is None:
                    try:
                        sp = serial.Serial(self.port, self.baud, bytesize=serial.EIGHTBITS,
                                           parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                                           timeout=self.serial_timeout, xonxoff=0, rtscts=0)
                        sp.flushInput()
                    except (serial.SerialException, OSError):
                        sp = None
                        time.sleep(0.1)

                print("Opened {}:{}".format(self.port, self.baud))

                try:
                    while True:
                        self.parser.put(sp.read(1000))

                        for timestamp, line, complete in self.parser:
                            print("{} : {}{}".format(log_time_str(timestamp), self.encoder(line),
                                                     "" if complete else " ..."))
                            self.logfile.write("{} : {}{}\n".format(log_time_str(timestamp), line,
                                                                    "" if complete else " ..."))
                            sys.stdout.flush()

                        time.sleep(0.01)

                except serial.SerialException as e:
                    print("Disconnected: %s, will try to open again ...".format(e.message))

            except KeyboardInterrupt:
                if sp is not None and sp.isOpen():
                    sp.close()
                    print("")
                    print("Closed {}:{}".format(self.port, self.baud))
                break


class DummyFileLog(object):
    def write(self, _):
        pass

    def close(self):
        pass

    def __str__(self):
        return "file DISABLED"


class FileLog(object):

    def __init__(self, logdir, port, baud):
        now = time.time()
        portname = os.path.basename(os.path.normpath(port))
        filename = "log_{}_{}.txt".format(portname, time.strftime("%Y%m%d_%H%M%SZ", time.gmtime(now)))
        latest = os.path.join(logdir, "log_{}_latest.txt".format(portname))

        self.path = os.path.join(logdir, filename)
        if not os.path.exists(logdir):
            os.makedirs(logdir)

        self.file = open(self.path, "wb", 0)
        self.file.write("# {} / {}\n".format(time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(now)),
                                             time.strftime("%Y-%m-%d %H:%M:%S%Z", time.localtime(now))))
        self.file.write("# {} : {}\n".format(port, baud))
        self.file.write("#-------------------------------------------------------------------------------\n")

        if os.path.islink(latest):
            os.unlink(latest)

        if hasattr(os, "symlink"):
            os.symlink(self.path, latest)

    def write(self, data):
        self.file.write(data)

    def close(self):
        self.file.close()

    def __str__(self):
        return self.path


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Serial logger")
    parser.add_argument("port", default="/dev/ttyUSB0", nargs='?')
    parser.add_argument("baud", default=115200, type=int, nargs='?')
    parser.add_argument("--hdlc", action="store_true")
    parser.add_argument("--nocolor", action="store_true")
    parser.add_argument("--logdir", default=os.environ.get("SERIAL_LOGGER_LOGDIR", os.path.expanduser("~/log")))
    parser.add_argument("--nolog", action="store_true")
    args = parser.parse_args()

    if args.hdlc:
        print("Using  {}:{} HDLC mode".format(args.port, args.baud))
        parser = LineParser()
        encoder = encode_hex_line
    else:
        if args.nocolor:
            encoder = nocolor_logger_line
        else:
            encoder = color_logger_line

        print("Using  {}:{} TEXT mode({}color)".format(args.port, args.baud, "no" if args.nocolor else ""))
        parser = LineParser(delimiter="\n", include_delimiter=False)

    if args.nolog:
        logfile = DummyFileLog()
    else:
        logfile = FileLog(args.logdir, args.port, args.baud)

    print("Logging to {}".format(logfile))

    SerialLogger(args.port, args.baud, parser, encoder, logfile).run()

    logfile.close()


if __name__ == "__main__":
    main()
