"""test_serial_logger.py: Some tests for parsers."""
import time
import unittest

from mote_serial_logger.mote_serial_logger import LineParser


class LineParserTest(unittest.TestCase):

    def test_hdlc(self):
        lp = LineParser()
        lp.put("\x7e\x7e\x7eaaa\x7e\x7ebbb\x7e\x7eaaa")
        timestamp, line, complete = next(lp)
        self.assertEqual(line, "\x7e\x7e")
        timestamp, line, complete = next(lp)
        self.assertEqual(line, "\x7eaaa\x7e")
        timestamp, line, complete = next(lp)
        self.assertEqual(line, "\x7ebbb\x7e")
        time.sleep(0.3)
        timestamp, line, complete = next(lp)
        self.assertEqual(line, "\x7eaaa")
        self.assertEqual(complete, False)

    def test_hdlc_delimiters(self):
        lp = LineParser(include_delimiter=False)
        lp.put("\x7e\x7e\x7eaaa\x7e\x7ebbb\x7e\x7eaaa")
        timestamp, line, complete = next(lp)
        self.assertEqual(line, "")
        timestamp, line, complete = next(lp)
        self.assertEqual(line, "aaa")
        timestamp, line, complete = next(lp)
        self.assertEqual(line, "bbb")
        time.sleep(0.3)
        timestamp, line, complete = next(lp)
        self.assertEqual(line, "aaa")
        self.assertEqual(complete, False)

    def test_newline(self):
        pass
