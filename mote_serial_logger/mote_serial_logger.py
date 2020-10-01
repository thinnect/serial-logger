#!/usr/bin/env python3
"""serial_logger.py: Serial port logger."""

import os
import sys
import time
import datetime
import binascii

import serial

__author__ = "Raido Pahtma"
__license__ = "MIT"


def log_time_str(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:23]


def nocolor_logger_line(line):
    return line.decode("ascii", "replace")


def color_logger_line(line):
    if isinstance(line, bytearray):
        line = line.decode("ascii", "replace")
    line = line.lstrip().rstrip()
    if line.startswith("E|"):
        return '\033[91m' + line + '\033[0m'
    if line.startswith("W|"):
        return '\033[93m' + line + '\033[0m'
    if line.startswith("I|"):
        return '\033[97m' + line + '\033[0m'
    return line


def encode_hex_line(line):
    return binascii.hexlify(bytearray(line)).decode("ascii", "replace").upper()


class LineParser(object):

    def __init__(self, delimiter=b'\x7e', include_delimiter=True, timeout=0.2):
        self.timestamp = time.time()
        self.delimiter = delimiter
        self.include_delimiter = include_delimiter
        self.timeout = timeout
        self.buf = bytearray()
        self.lines = []

    def clear(self):
        self.buf =bytearray()
        self.lines = []

    def put(self, data):
        if data:
            timestamp = time.time()

            if len(self.buf) == 0:
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

    def __next__(self):
        if len(self.lines) > 0:
            timestamp, line = self.lines.pop(0)
            return timestamp, line, True
        else:
            if self.buf and time.time() - self.timestamp > self.timeout:
                t = self.buf
                if not self.include_delimiter:
                    t = t.rstrip(self.delimiter).lstrip(self.delimiter)
                self.buf = bytearray()
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
                    if sys.platform.startswith('linux'):
                        if os.path.exists(self.port):
                            if 0 != os.system("setserial {} low_latency".format(self.port)):
                                print("Failed to configure port for low_latency")
                        else:
                            time.sleep(0.1)
                            continue

                    try:
                        sp = serial.serial_for_url(self.port,
                                                   baudrate=self.baud,
                                                   bytesize=serial.EIGHTBITS,
                                                   parity=serial.PARITY_NONE,
                                                   stopbits=serial.STOPBITS_ONE,
                                                   timeout=self.serial_timeout,
                                                   xonxoff=False,
                                                   rtscts=False, dsrdtr=False,
                                                   exclusive=True,
                                                   do_not_open=True)
                        sp.dtr = 0  # Set initial state to 0
                        sp.rts = 0  # Set initial state to 0
                        sp.open()
                        sp.flushInput()
                    except (serial.SerialException, OSError):
                        sp = None
                        time.sleep(0.1)

                print("Opened {}:{}".format(self.port, self.baud))

                try:
                    while True:
                        self.parser.put(sp.read_until(self.parser.delimiter))

                        for timestamp, line, complete in self.parser:
                            print("{} : {}{}".format(log_time_str(timestamp), self.encoder(line),
                                                     "" if complete else " ..."))
                            self.logfile.write("{} : {}{}\n".format(log_time_str(timestamp), line.decode("ascii", "replace"),
                                                                    "" if complete else " ..."))
                            sys.stdout.flush()

                        # time.sleep(0.01)

                except serial.SerialException as e:
                    print("Disconnected: {}, will try to open again ...".format(e))

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

        self.file = open(self.path, "w")
        self.file.write("# {} / {}\n".format(time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(now)),
                                             time.strftime("%Y-%m-%d %H:%M:%S%Z", time.localtime(now))))
        self.file.write("# {} : {}\n".format(port, baud))
        self.file.write("#-------------------------------------------------------------------------------\n")
        self.file.flush()

        if os.path.islink(latest):
            os.unlink(latest)

        if hasattr(os, "symlink"):
            os.symlink(self.path, latest)

    def write(self, data):
        self.file.write(data)
        self.file.flush()

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
        parser = LineParser(delimiter=b'\n', include_delimiter=False)

    if args.nolog:
        logfile = DummyFileLog()
    else:
        logfile = FileLog(args.logdir, args.port, args.baud)

    print("Logging to {}".format(logfile))

    SerialLogger(args.port, args.baud, parser, encoder, logfile).run()

    logfile.close()


if __name__ == "__main__":
    main()
