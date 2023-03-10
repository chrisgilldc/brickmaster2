####
#
# BRICKMASTER2
#
####

## Summary

A (Circuit)Python application for controlling relays and devices.

This is a rewrite of my original BrickMaster Flask app. Major changes:

* Communication via MQTT, no more REST API
* CircuitPython, supports CircuitPython boards as well as Pi boards
* Support for a variety of interface boards:
  * 8Relay board
  * Any relay via GPIO
  * Lego Power Functions via IR - PLANNED
  * Lego PoweredUp via Bluetooth - PLANNED

## Platform Support

### Supported Platforms
This was *intended* to be written in CircuitPython to support both the CircuitPython boards and general-purpose Linux 
SBCs (ie: the Pi). Due to [a bug](https://github.com/adafruit/Adafruit_CircuitPython_MiniMQTT/issues/148) in MiniMQTT, 
CircuitPython support is not currently possible and only general-purpose Linux systems are supported.

### Tested Boards

BrickMaster2 has been tested directly on the following boards:
* Raspberry Pi Zero W
* Adafruit Metro M4 Airlift

If you find other boards to work, please note it so this document can be updated.

### Board/Feature Matrix

Some features are only supported on certain board-types. A support matrix will be inserted here.

### Bluetooth
sudo setcap cap_net_raw+e      <PATH>/bluepy-helper
sudo setcap cap_net_admin+eip   <PATH>/bluepy-helper


## Installation

### Linux

Assumes Raspberry Pi OS/Rasbian on a Pi.

_Probably works for other Linux versions, but not tested, adapt as appropriate._

1. Fetch the package to an appropriate directory. Assumed here you're using /home/pi/brickmaster2
2. Install all required python packages
   `pip3 install -r requirements.txt`
3. Copy the example systemd unit to ~/.config/systemd/user.
4. Edit the systemd unit if necessary, ie: if you're using an alternate path.
5. Ask systemd to reload user units - `systemctl --user daemon-reload`
6. Enable the unit - `systemctl --user enable brickmaster2.service`
7. 
