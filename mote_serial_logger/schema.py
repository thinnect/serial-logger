#!/usr/bin/env python3
"""schema.py: Scho file reading functions """
import json

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