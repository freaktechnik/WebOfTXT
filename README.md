# Web of TXT

Basic mapping layer between a [fischertechnik Robo TXT Controller](https://www.fischertechnik.de/en/products/playing/robotics/522429-robotics-txt-controller) and the [Web of Things](https://iot.mozilla.org/things/). Runs
on the [community firmware](https://cfw.ftcommunity.de/ftcommunity-TXT).

## Adapted I/O

- All inputs as either a button, resistor, ultrasonic, voltage, line follower or color sensor.
- All actors as either motor or single lamp output
- Counters as read-only numbers and a reset action
- Playing a built-in sound via action
- Input voltage
- Reference voltage
- TXT system temperature
- Camera

### Potential I/O

- I2C sensors

## Build

Run `./build.sh` to generate a zip file that can then be installed on the TXT via web UI.
This expects there to be a python 3 binary called `python3` to download all necessary dependencies.

## Quirks

- Inputs are refreshed approximately every second, this may lead to flicker on consumers (the official Mozilla gateway for example).
- Stopping and re-starting the server may not behave properly and errors will not be surfaced.
- Configuration of inputs and outputs is not persisted.

## Demo

https://www.youtube.com/watch?v=4uicH0LA2Qo
