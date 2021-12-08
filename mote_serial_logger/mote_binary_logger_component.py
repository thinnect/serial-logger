#!/usr/bin/env python3
"""mote_binary_logger_component.py: Formating of  """
from schema import *
import time
import sys


from enum import Enum

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
        print("Formating :" + fmt)
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
            string = ""
            string.append(res)
            string.append(data[len(data)])
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
                value = int.from_bytes(data[pos:pos+8], byteorder='big',signed=True)
                args.append(value)
                pos += 8
            elif type == DataTypes.UINT64:
                value = int.from_bytes(data[pos:pos+8], byteorder='big',signed=False)
                args.append(value)
                pos += 8
            elif type == DataTypes.INT32:
                value = int.from_bytes(data[pos:pos+4], byteorder='big',signed=True)
                args.append(value)
                pos += 4
            elif type == DataTypes.UINT32:
                value = int.from_bytes(data[pos:pos+4], byteorder='big',signed=False)
                args.append(value)
                pos += 4
            elif type == DataTypes.INT16:
                value = int.from_bytes(data[pos:pos+2], byteorder='big',signed=True)
                args.append(value)
                pos += 2
            elif type == DataTypes.UINT16:
                value = int.from_bytes(data[pos:pos+2], byteorder='big',signed=False)
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

        return res
    
    def put(self, data):
        if data:
            print("Inside put Data is :" + str(data))
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