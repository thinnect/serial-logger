"""
mote-serial-log: Mote serial logger with output coloring.
Log printf and HDLC messages from serial port to terminal and logfile.
"""

from setuptools import setup
from os.path import join as pjoin

from mote_serial_logger import mote_serial_logger

doclines = __doc__.split("\n")

setup(name='mote_serial_logger',
      version=mote_serial_logger.version,
      description='Mote serial logger with output coloring.',
      long_description='\n'.join(doclines[2:]),
      url='http://github.com/thinnect/serial-logger',
      author='Raido Pahtma',
      author_email='raido@thinnect.com',
      license='MIT',
      platforms=['any'],
      packages=['mote_serial_logger'],
      install_requires=["pyserial"],
      test_suite='nose.collector',
      tests_require=['nose'],
      scripts=[pjoin('bin', 'serial-logger'), pjoin('bin', 'tail-serial-log')],
      zip_safe=False)
