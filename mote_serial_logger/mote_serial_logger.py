#!/usr/bin/env python3
"""serial_logger.py: Serial port logger."""

import os
import sys
import time
import datetime
import binascii
import serial

import json
from enum import Enum

__author__ = "Raido Pahtma"
__license__ = "MIT"


class LogMessage:
    def __init__(self, linenr, fmt, severity):
        self.m_line_nr = linenr
        self.m_format = fmt
        self.m_severity = severity
    
    def GetFormat(self):
        return self.m_format
    
    def GetLinenr(self):
        return self.m_line_nr

    def GetSeverity(self):
        return self.m_severity


class Module:
    def __init__(self, name, id, logs):
        self.m_logs = logs
        self.m_name = name
        self.m_id = id
    
    def GetName(self):
        return self.m_name
    
    def GetId(self):
        return self.m_id
    
    def GetLogs(self):
        return self.m_logs

def deserilize_logs(logs):
    lgs = []
    for a in logs:
        lgs.append(LogMessage(a['linenr'],a['format'],a['severity']))
    return lgs

def deserilize_scho(file):
    modules = []
    data = open(file)
    js = json.load(data)
    for a in js:
        modules.append(Module(a['name'],a['id'], deserilize_logs(a['logs'])))

    return modules

class DataTypes(Enum):
    INT16 = 0
    INT32 = 1
    INT64 = 2
    UINT16 = 3
    UINT32 = 4
    UINT64 = 5
    POINTER = 6
    DOUBLE = 7
    STRING = 8

class BinaryParser(object):
    def __init__(self, file, delimiter=b'\x7e', include_delimiter=False, timeout=0.2):
        self.timestamp = time.time()
        self.delimiter = delimiter
        self.include_delimiter = include_delimiter
        self.timeout = timeout
        self.buf = bytearray()
        self.lines = []
        self.modules = deserilize_scho(file)

    def clear(self):
        self.buf =bytearray()
        self.lines = []

    def isFormatElement(self, element):
        predef = ['d','i','u','x','f','s','p']
        for e in predef:
            if e == element.lower():
                return True
    
        return False

    def SplitFormatters(self, string):
        formatters = []
        found_percentage = False
        start = 0
        for element in range(0, len(string)):
            if found_percentage is not True and string[element] == '%':
                start = element
                found_percentage = True
            if found_percentage is True and self.isFormatElement(string[element]) is True:
                formatters.append(string[start+1:element+1])
                start = 0
                found_percentage = False

        return formatters

    def replace_str_index(self, text,start=0, end=0,replacement=''):
        return '%s%s%s'%(text[:start],replacement,text[end+1:])

    def ReplaceFormatters(self, fmt, data):
        found_percentage = False
        res = fmt
        start = 0
        i = 0
        Done = False
        while Done is not True:
            start = 0
            found_percentage = False
            if res.find('%') == -1:
                Done = True
                break
            for element in range(0, len(res)):
                if found_percentage is not True and res[element] == '%':
                    start = element
                    found_percentage = True
                if found_percentage is True and self.isFormatElement(res[element]) is True:
                    res = self.replace_str_index(res, start, element, str(data[i]))
                    i += 1
                    break
        
        # All data is not formated which means there is a buffer included
        if i != len(data):
            print(data)
            string = res +  " 0x" + data[len(data) - 1].hex()
            res = string
        
        return res


    def GetArguments(self, formats, data):
        #Convert formats to datatypes
        args = []
        types = []
        pos = 0
        for d in formats:
            d = d.lower()
            if d.find('ll') != -1:
                if d[-1] == 'i' or d[-1] == 'd':
                    types.append(DataTypes.INT64)
                elif d[-1] == 'u' or d[-1] == 'x':
                    types.append(DataTypes.UINT64)
            elif d.find('l') != -1:
                if d[-1] == 'i' or d[-1] == 'd':
                    types.append(DataTypes.INT32)
                elif d[-1] == 'u' or d[-1] == 'x':
                    types.append(DataTypes.UINT32)
            else:
                if d[-1] == 'i' or d[-1] == 'd':
                    types.append(DataTypes.INT16)
                elif d[-1] == 'u' or d[-1] == 'x':
                    types.append(DataTypes.UINT16)
                elif d[-1] == 'p':
                    types.append(DataTypes.POINTER)
                elif d[-1] == 'f':
                    types.append(DataTypes.DOUBLE)
                elif d[-1] == 's':
                    types.append(DataTypes.STRING)
    
        for type in types:
            if type == DataTypes.INT64:
                value = int.from_bytes(data[pos:pos+8], byteorder='little',signed=True)
                args.append(value)
                pos += 8
            elif type == DataTypes.UINT64:
                value = int.from_bytes(data[pos:pos+8], byteorder='little',signed=False)
                args.append(value)
                pos += 8
            elif type == DataTypes.INT32:
                value = int.from_bytes(data[pos:pos+4], byteorder='little',signed=True)
                args.append(value)
                pos += 4
            elif type == DataTypes.UINT32:
                value = int.from_bytes(data[pos:pos+4], byteorder='little',signed=False)
                args.append(value)
                pos += 4
            elif type == DataTypes.INT16:
                value = int.from_bytes(data[pos:pos+2], byteorder='little',signed=True)
                args.append(value)
                pos += 2
            elif type == DataTypes.UINT16:
                value = int.from_bytes(data[pos:pos+2], byteorder='little',signed=False)
                args.append(value)
                pos += 2
            elif type == DataTypes.POINTER:
                args.append(str(data[pos:pos+4]))
                pos += 4
            elif type == DataTypes.DOUBLE:
                args.append(data[pos:pos+4])
                pos += 4
            elif type == DataTypes.STRING:
                end_pos = pos
                while True:
                    if data[end_pos] == 0:
                        break
                    end_pos +=1
                args.append(data[pos:end_pos])
                pos += (end_pos - pos)


        # There is data left probably buffer
        if len(data) != pos:
            args.append(data[pos:len(data)])

        return args
    
    def get_message(self, line):
        packet = bytearray(line)
        mod_id = int.from_bytes(packet[0:2], byteorder='big', signed=False) #
        line_nr = int.from_bytes(packet[2:4], byteorder='big', signed=False) #
        data = packet[4:len(packet)]
        fmtstring = ""
        formatters = []
        args = []
        res = ""


        for mod in self.modules:
            if mod.GetId() == mod_id:
                for log in mod.GetLogs():
                    if log.GetLinenr() == line_nr:
                        fmtstring = log.GetFormat()
                        formatters = self.SplitFormatters(fmtstring)
                        args = self.GetArguments(formatters,data)
                        res = self.ReplaceFormatters(fmtstring,args)
                        severity_ = ["I","W","E","D"]
                        severity_str = severity_[log.GetSeverity()] + "|" + mod.GetName() + ":" + str(log.GetLinenr()) + "|"
                        res = severity_str + res

        if res == "":
            res = "Undefined log"
            

        return res
    
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
                    
                    self.lines.append((self.timestamp, self.get_message(t)))
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

def binary_hex_line(line):
    return line

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
        self.serial_timeout = 0.01
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
                            #self.logfile.write("{} : {}{}\n".format(log_time_str(timestamp), line.decode("ascii", "replace"),
                            #                                        "" if complete else " ..."))
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

        if hasattr(os, "symlink"):
            if os.path.islink(latest):
                os.unlink(latest)

            try:
                os.symlink(self.path, latest)
            except OSError:
                print("Failed to create symlink {} -> {}". format(latest, self.path))

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
    parser.add_argument("--binary", default="", nargs='?')
    args = parser.parse_args()

    if args.hdlc:
        print("Using  {}:{} HDLC mode".format(args.port, args.baud))
        parser = LineParser()
        encoder = encode_hex_line
    elif args.binary:
        print("Using  {}:{} Binary mode".format(args.port, args.baud))
        parser = BinaryParser(args.binary)
        encoder = binary_hex_line
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
