# mote-serial-logger
Serial debug message and HDLC message logger.

## Installation
Install with **pip**. This will add scripts **serial-logger** and **tail-serial-log** to the path.

## Example
Specify port and baudrate.

```serial-logger /dev/ttyUSB0 115200```

## HDLC mode
HDLC mode is activated with the **--hdlc** switch. Messages are expected to be framed with 0x7E bytes. Escape bytes are
not processed.

## Logfiles
The serial-logger always logs data to a file, unless the **--nolog** option is given. The default logging path is ```~/log```, but
it can also be specified with **--logdir** or through the environment with ```SERIAL_LOGGER_LOGDIR```.

## Tailing
The package includes a special **tail-serial-log** command that also supports log coloring. When using regular **tail**, it
is best to point tail at the log_PORTNAME_latest.txt file with the capital **-F** option. ```tail -F log_PORTNAME_latest.txt``` will detect changes
to the symlink.

## PyInstaller

mote-serial-logger can be packaged into a Windows executable. For that you need to install PyInstaller with
```python -m pip install pyinstaller```. All dependencies(requirements.txt) need to be installed on the build machine.
The executable can be created by running the ```build.bat``` batch file. ```serial-logger.exe``` should then get created in the dist directory.
