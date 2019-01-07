# Web of TXT

Basic mapping layer between a [fischertechnik TXT](https://www.fischertechnik.de/de-de/produkte/spielen/robotics/522429-robotics-txt-controller) and the [Web of Things](https://iot.mozilla.org/things/). Runs
on the [community firmware](https://cfw.ftcommunity.de/ftcommunity-TXT).

## Adapted I/O
- All inputs as either a button, resistor, ultrasonic, voltage or color sensor.
- All actors as either motor or single lamp output
- Counters as read-only numbers and a reset action
- Playing a built-in sound via action
- Input voltage
- Reference voltage
- TXT system temperature

### Potential I/O
- Camera
- I2C things

## Build

Run `./build.sh` to generate a zip file that can then be installed on the TXT via web UI.
This expects there to be a python 3 binary called `python3` to download all necessary dependencies.
