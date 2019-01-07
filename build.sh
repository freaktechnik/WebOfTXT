#! /bin/sh
python3 -m pip install -U --target=. --platform=linux_armv7l --only-binary=:all: --no-compile --extra-index-url=https://www.piwheels.org/simple -r requirements.txt
zip -r WebOfTXT.zip main.py icon.png manifest ifaddr jsonschema pyee tornado webthing zeroconf.py netifaces.cpython-35m-arm-linux-gnueabihf.so
