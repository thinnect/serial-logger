import unittest

import time

from serial_logger import LineParser

class LineParserTest(unittest.TestCase):

    def test_hdlc(self):
        lp = LineParser()
        lp.put("\x7e\x7e\x7eaaa\x7e\x7ebbb\x7e\x7eaaa")
        timestamp, line, complete = lp.next()
        self.assertEqual(line, "7E7E")
        timestamp, line, complete = lp.next()
        self.assertEqual(line, "7E6161617E")
        timestamp, line, complete = lp.next()
        self.assertEqual(line, "7E6262627E")
        time.sleep(0.3)
        timestamp, line, complete = lp.next()
        self.assertEqual(line, "7E616161")
        self.assertEqual(complete, False)

    def test_hdlc_delimiters(self):
        lp = LineParser(include_delimiter=False)
        lp.put("\x7e\x7e\x7eaaa\x7e\x7ebbb\x7e\x7eaaa")
        timestamp, line, complete = lp.next()
        self.assertEqual(line, "")
        timestamp, line, complete = lp.next()
        self.assertEqual(line, "616161")
        timestamp, line, complete = lp.next()
        self.assertEqual(line, "626262")
        time.sleep(0.3)
        timestamp, line, complete = lp.next()
        self.assertEqual(line, "616161")
        self.assertEqual(complete, False)

    def test_newline(self):
    	pass
