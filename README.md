# uPythonHelper
uPython Serial Communication Utility

## Disclaimer ##
This allows you to make changes to your uPython device.  If you delete your files, you'll probably need to reflash your device. 

## Prerequisites ##
* MicroPython - https://micropython.org/
* Python 3.6 (earlier versions might work) - https://www.python.org/downloads/release/python-360/
* Tkinter - https://wiki.python.org/moin/TkInter
* serial-device2  - https://pypi.python.org/simple/serial-device2/

## Functionality ##
* Terminal Access
* List files (root only, no directory recursing)
* Upload files from computer to device
* Download files to computer from device
* Delete files from the device

## Compatibility ##
* This has only been tested with Windows.  It might work on Linux or Mac with the proper device name in the Port/Device field.
* It supports 115200 bps.  If you need something else, change the file.  If you want to provide UI, send a nice pull request!
* I use this with my NodeMCU + MicroPython v1.8.4-10-gbc28ac8 on 2016-09-09; ESP module with ESP8266
