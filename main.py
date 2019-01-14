#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import ftrobopy
import webthing
import threading
import asyncio
import uuid
import os
from pathlib import Path
import cv2
import time
import base64
import urllib
from copy import copy
from TouchStyle import *

# TODO camera -> https://iot.mozilla.org/schemas/#Camera
# TODO persist last configuration?
# https://github.com/ftrobopy/ftrobopy/blob/master/manual.pdf


class SoundAction(webthing.Action):
    SOUNDS = [
        'Stop',
        'Flugzeug',
        'Alarm',
        'Glocke',
        'Bremsen',
        'Autohupe (kurz)',
        'Autohupe (lang)',
        'Brechendes Holz',
        'Bagger',
        'Fantasie 1',
        'Fantasie 2',
        'Fantasie 3',
        'Fantasie 4',
        'Bauernhof',
        'Feuerwehrsirene',
        'Feuerstelle',
        'Formel 1 Auto',
        'Hubschrauber',
        'Hydraulik',
        'Laufender Motor',
        'Startender Motor',
        'Propeller-Flugzeug',
        'Achterbahn',
        'Schiffshorn',
        'Traktor',
        'LKW',
        'Augenzwinkern',
        'Fahrgeräusch',
        'Kopf heben',
        'Kopf neigen'
    ]

    def __init__(self, thing, input_):
        webthing.Action.__init__(
            self,
            uuid.uuid4().hex,
            thing,
            'playSound',
            input_=input_
        )

    def perform_action(self):
        self.thing.txt.play_sound(
            self.SOUNDS.index(self.input['sound']),
            1,
            self.input['volume']
        )

    def cancel(self):
        self.thing.txt.stop_sound()


class ResetCounterAction(webthing.Action):
    COUNTERS = [
        'C1',
        'C2',
        'C3',
        'C4'
    ]

    def __init__(self, thing, input_):
        webthing.Action.__init__(
            self,
            uuid.uuid4().hex,
            thing,
            'resetCounter',
            input_=input_
        )

    def perform_action(self):
        self.thing.txt.incrCounterCmdId(self.COUNTERS.index(self.input))


class PressedEvent(webthing.Event):
    def __init__(self, thing, button):
        webthing.Event.__init__(self, thing, 'pressedEvent' + button)


class ServerThread(threading.Thread):
    def __init__(self, server):
        super(ServerThread, self).__init__()
        self.server = server

    def run(self):
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        self.server.start()

    def stop(self):
        self.server.stop()
        self.event_loop.stop()


class CameraProperty(webthing.Property):
    def __init__(self, thing, name, cam, metadata=None):
        super(CameraProperty, self).__init__(
            thing,
            name,
            webthing.Value(None),
            metadata
        )
        self.cam = cam
        self.cap = None
        self.last_update = None
        self.metadata['@type'] = 'ImageProperty'

    def start_cap(self):
        self.cap = cv2.VideoCapture(self.cam)
        if self.cap.isOpened():
            self.cap.set(3, 320)
            self.cap.set(4, 240)
            self.cap.set(5, 10)

    def stop_cap(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = None
        self.last_update = None

    def capture(self):
        if self.last_update is not None and self.last_update + 0.1 > time.time():
            return

        self.last_update = time.time()
        frame = self.cap.read()[1]
        retval, image = cv2.imencode('.jpg', frame)
        self.image = 'data:image/jpeg;base64,' + base64.b64encode(image).decode('ascii')

    def as_property_description(self):
        description = copy(self.metadata)
        if self.cap is not None:
            description['links'] = [
                {
                    'href': self.image,
                    'mediaType': 'image/jpeg'
                }
            ]
        return description


class wotApplication(TouchApplication):
    COLOR_MAP = {
        'rot': '#ff0000',
        'blau': '#0000ff',
        'weiss': '#ffffff'
    }

    def __init__(self, args):
        TouchApplication.__init__(self, args)

        self.w = TouchWindow('WebOfTXT')

        try:
            self.txt = ftrobopy.ftrobopy('localhost', 65000)
        except:
            self.txt = None

        self.outputs = [
            self.txt.C_OUTPUT,
            self.txt.C_OUTPUT,
            self.txt.C_OUTPUT,
            self.txt.C_OUTPUT
        ]
        self.inputs = [
            (self.txt.C_SWITCH, self.txt.C_DIGITAL),
            (self.txt.C_SWITCH, self.txt.C_DIGITAL),
            (self.txt.C_SWITCH, self.txt.C_DIGITAL),
            (self.txt.C_SWITCH, self.txt.C_DIGITAL),
            (self.txt.C_SWITCH, self.txt.C_DIGITAL),
            (self.txt.C_SWITCH, self.txt.C_DIGITAL),
            (self.txt.C_SWITCH, self.txt.C_DIGITAL),
            (self.txt.C_SWITCH, self.txt.C_DIGITAL)
        ]
        self.sensors = [
            'pushbutton',
            'pushbutton',
            'pushbutton',
            'pushbutton',
            'pushbutton',
            'pushbutton',
            'pushbutton',
            'pushbutton'
        ]

        self.inputButtons = []
        self.outputButtons = []
        self.cams = []

        if not self.txt:
            err_msg = QLabel('Error connectiong to IO server')
            err_msg.setWordWrap(True)
            err_msg.setAlignment(Qt.AlignCenter)
            self.w.setCentralWidget(err_msg)
        else:
            self.thing = webthing.Thing(
                self.txt.getDevicename(),
                ['MultiLevelSwitch'],
                'fischertechnik TXT ' + str(self.txt.getVersionNumber())
            )
            self.server = None
            self.thing.txt = self.txt
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_level)
            for i in range(0, 4):
                self.addCounter(i)
            self.addResetCounters()

            self.addPlaySound()
            self.addStateProps()

            givenCam = os.environ.get('FTC_CAM')
            cam = None
            if givenCam is None:
                cam = 0
            else:
                cam = int(givenCam)

            camPath = Path('/dev/video' + str(cam))
            if camPath.exists():
                self.addCamera(cam)

            main_page = self.buildMainPage()
            input_page = self.buildInputPage()
            output_page = self.buildOutputPage()

            tabBar = QTabWidget()
            tabBar.addTab(main_page, 'Start')
            tabBar.addTab(input_page, 'Inputs')
            tabBar.addTab(output_page, 'Outputs')
            self.w.setCentralWidget(tabBar)

        self.w.show()
        self.exec_()

    def buildMainPage(self):
        page = QWidget()
        vbox = QVBoxLayout()
        button = QPushButton('start')
        button.clicked.connect(self.start)
        vbox.addWidget(button)
        page.setLayout(vbox)
        return page

    def buildInputPage(self):
        page = QWidget()
        vbox = QVBoxLayout()
        for input in range(1, 9):
            hbox = QHBoxLayout()
            title = QLabel('I' + str(input))
            hbox.addWidget(title)
            type = QPushButton('pushbutton')
            type.clicked.connect(self.toggleInputType)
            hbox.addWidget(type)
            vbox.addLayout(hbox)
            self.inputButtons.append(type)
        page.setLayout(vbox)
        return page

    def buildOutputPage(self):
        page = QWidget()
        vbox = QVBoxLayout()
        for output in range(1, 5):
            hbox = QHBoxLayout()
            title = QLabel('M' + str(output))
            hbox.addWidget(title)
            type = QPushButton('motor')
            type.clicked.connect(self.toggleOutputType)
            hbox.addWidget(type)
            vbox.addLayout(hbox)
            self.outputButtons.append(type)
        page.setLayout(vbox)
        return page

    def toggleInputType(self):
        rec = self.sender()
        if rec.text() == 'pushbutton':
            rec.setText('resistor')
        elif rec.text() == 'resistor':
            rec.setText('ultrasonic')
        elif rec.text() == 'ultrasonic':
            rec.setText('voltage')
        elif rec.text() == 'voltage':
            rec.setText('linesens')
        elif rec.text() == 'linesens':
            rec.setText('colorsens')
        else:
            rec.setText('pushbutton')

    def toggleOutputType(self):
        rec = self.sender()
        if rec.text() == 'motor':
            rec.setText('light')
        else:
            rec.setText('motor')

    def getSensorValue(self, index, type):
        if type == 'pushbutton':
            rawValue = self.txt.input(index + 1).state() == 1
        elif type == 'resistor':
            try:
                rawValue = self.txt.resistor(index + 1).value()
            except:
                rawValue = self.txt.resistor(index + 1).resistance()
        elif type == 'ultrasonic':
            rawValue = self.txt.ultrasonic(index + 1).distance() / 100
        elif type == 'voltage':
            rawValue = self.txt.voltage(index + 1).voltage() / 1000
        elif type == 'linesens':
            rawValue = self.txt.trailfollower(index + 1).state()
        elif type == 'colorsens':
            color = self.txt.colorsensor(index + 1).color()
            if color not in self.COLOR_MAP:
                rawValue = color
            else:
                rawValue = self.COLOR_MAP[color]
        return rawValue

    def addCapability(self, capability):
        if capability not in self.thing.type:
            self.thing.type.append(capability)

    def addSensor(self, index, type):
        unit = None
        semanticType = None
        name = 'I' + str(index + 1)

        if type == 'pushbutton':
            rawType = 'boolean'
            semanticType = 'PushedProperty'
            self.addCapability('PushButton')
            self.inputs[index] = (self.txt.C_SWITCH, self.txt.C_DIGITAL)
            self.thing.add_available_event('pressedEvent' + name, {
                '@type': 'PressedEvent',
                'title': name + ' pressed'
            })
        elif type == 'resistor':
            rawType = 'number'
            unit = 'Ohm'
            self.inputs[index] = (self.txt.C_RESISTOR, self.txt.C_ANALOG)
        elif type == 'ultrasonic':
            rawType = 'number'
            unit = 'meter'
            self.inputs[index] = (self.txt.C_ULTRASONIC, self.txt.C_ANALOG)
        elif type == 'voltage':
            rawType = 'number'
            unit = 'volt'
            semanticType = 'VoltageProperty'
            self.inputs[index] = (self.txt.C_VOLTAGE, self.txt.C_ANALOG)
        elif type == 'linesens':
            rawType = 'boolean'
            semanticType = 'BooleanProperty'
            self.addCapability('BinarySensor')
            self.inputs[index] = (self.txt.C_SWITCH, self.txt.C_DIGITAL)
        elif type == 'colorsens':
            rawType = 'string'
            self.inputs[index] = (self.txt.C_VOLTAGE, self.txt.C_ANALOG)
            semanticType = 'ColorProperty'

        self.sensors[index] = type
        value = webthing.Value(self.getSensorValue(index, type))

        self.thing.add_property(
            webthing.Property(
                self.thing,
                name,
                value,
                metadata={
                    'title': name,
                    'type': rawType,
                    'readOnly': True,
                    'unit': unit,
                    '@type': semanticType
                }
            )
        )

    def addActor(self, index, type):
        if type == 'motor':
            self.outputs[index] = self.txt.C_MOTOR
            plug = 'M' + str(index + 1)
            self.thing.add_property(
                webthing.Property(
                    self.thing,
                    plug,
                    webthing.Value(
                        0,
                        lambda new_value: self.update_output(index, new_value)
                    ),
                    metadata={
                        '@type': 'LevelProperty',
                        'title': plug,
                        'type': 'integer',
                        'minimum': -512,
                        'maximum': 512
                    }
                )
            )
        elif type == 'light':
            self.outputs[index] = self.txt.C_OUTPUT
            for offset in range(1, 3):
                self.addLight(index, offset)

    def addLight(self, index, offset):
        plug = 'O' + str((index * 2) + offset)
        self.thing.add_property(
            webthing.Property(
                self.thing,
                plug,
                webthing.Value(
                    1,
                    lambda new_value: self.update_output(
                        index,
                        new_value,
                        offset
                    )
                ),
                metadata={
                    '@type': 'LevelProperty',
                    'title': plug,
                    'type': 'integer',
                    'minimum': 1,
                    'maximum': 512
                }
            )
        )

    def addCounter(self, index):
        self.thing.add_property(
            webthing.Property(
                self.thing,
                'C' + str(index + 1),
                webthing.Value(self.txt.getCurrentCounterValue(index)),
                metadata={
                    'type': 'integer',
                    'minimum': 0,
                    'readOnly': True
                }
            )
        )

    def addResetCounters(self):
        self.thing.add_available_action(
            'resetCounter',
            {
                'title': 'Reset counter',
                'description': 'Reset C1-C4',
                'input': {
                    'type': 'string',
                    'enum': ResetCounterAction.COUNTERS
                }
            },
            ResetCounterAction
        )

    def addPlaySound(self):
        self.thing.add_available_action(
            'playSound',
            {
                'title': 'Play sound',
                'description': 'Play a sound on the TXT',
                'input': {
                    'type': 'object',
                    'required': [
                        'sound'
                    ],
                    'properties': {
                        'sound': {
                            'type': 'string',
                            'enum': SoundAction.SOUNDS
                        },
                        'volume': {
                            'type': 'integer',
                            'default': 100,
                            'minimum': 0,
                            'maximum': 100
                        }
                    }
                }
            },
            SoundAction
        )

    def addStateProps(self):
        self.thing.add_property(
            webthing.Property(
                self.thing,
                'inputVoltage',
                webthing.Value(self.txt.getPower() / 1000),
                metadata={
                    '@type': 'VoltageProperty',
                    'type': 'number',
                    'readOnly': True,
                    'unit': 'volt',
                    'title': 'Input voltage'
                }
            )
        )
        self.thing.add_property(
            webthing.Property(
                self.thing,
                'refVoltage',
                webthing.Value(self.txt.getReferencePower() / 1000),
                metadata={
                    '@type': 'VoltageProperty',
                    'type': 'number',
                    'readOnly': True,
                    'unit': 'volt',
                    'title': 'Reference voltage'
                }
            )
        )
        self.thing.add_property(
            webthing.Property(
                self.thing,
                'temperature',
                webthing.Value(self.txt.getTemperature()),
                metadata={
                    # '@type': 'TemperatureProperty',
                    'type': 'number',
                    'readOnly': True,
                    'title': 'Temperature'
                    # 'unit': 'degrees celsius'
                }
            )
        )

    def addCamera(self, cam):
        self.thing.add_property(
            CameraProperty(
                self.thing,
                'camera' + str(cam),
                cam,
                metadata={
                    'title': 'Camera'
                }
            )
        )
        self.addCapability('Camera')
        self.cams.append(cam)

    def startCams(self):
        for cam in self.cams:
            self.thing.find_property('camera' + str(cam)).start_cap()

    def stopCams(self):
        for cam in self.cams:
            self.thing.find_property('camera' + str(cam)).stop_cap()

    def capCams(self):
        for cam in self.cams:
            self.thing.find_property('camera' + str(cam)).capture()

    def start(self):
        rec = self.sender()
        rec.setDisabled(True)
        if self.server is None:
            self.txt.setConfig(self.outputs, self.inputs)
            self.txt.updateConfig()

            # TODO remove all existing stuff on the thing

            for index, inputButton in enumerate(self.inputButtons):
                self.addSensor(index, inputButton.text())

            for index, outputButton in enumerate(self.outputButtons):
                self.addActor(index, outputButton.text())

            if self.server is None:
                self.server = webthing.WebThingServer(
                    webthing.SingleThing(self.thing),
                    port=8888
                )
            self.thread = ServerThread(self.server)

            self.timer.start(1000)
            self.startCams()

            try:
                self.thread.start()
                rec.setText('stop')
                rec.setDisabled(False)
            except:
                self.thread.stop()
                self.server.stop()
                self.stopCams()
                self.server = None
                self.thread = None
        else:
            self.thread.stop()
            self.thread = None
            self.server = None
            self.timer.stop()
            self.stopCams()
            rec.setText('start')
            rec.setDisabled(False)

    def update_output(self, index, value, offset=1):
        if self.outputs[index] == self.txt.C_MOTOR:
            self.txt.motor(index + offset).setSpeed(value)
        else:
            self.txt.output((index * 2) + offset).setLevel(value)

    def set_property(self, name, value, prop=None):
        if not prop:
            prop = self.thing.find_property(name)
        if not prop:
            return

        if prop.value.get() != value:
            prop.value.notify_of_external_update(value)

    def update_level(self):
        # Update inputs
        new_values = self.txt.getCurrentInput()
        for index, new_value in enumerate(new_values):
            name = 'I' + str(index + 1)
            type = self.sensors[index]
            prop = self.thing.find_property(name)
            if type == 'pushbutton' and not prop.value.get() and new_value == 1:
                self.thing.add_event(PressedEvent(self.thing, name))
            # TODO filter analog values to avoid flickering
            self.set_property(
                name,
                self.getSensorValue(index, type)
            )

        # Update counters
        counter_changed = self.txt.getCurrentCounterInput()
        for index, changed in enumerate(counter_changed):
            if changed != 0:
                name = 'C' + str(index + 1)
                self.set_property(
                    name,
                    self.mot(index + 1).getCurrentDistance()
                )

        # Update outputs - shouldn't have to update them.
        # for index, output in enumerate(self.outputs):
        #     if output == self.txt.C_MOTOR:
        #         value = 0
        #         for i in range(0, 2):
        #             pwm = self.txt.getPwm((index * 2) + i)
        #             if pwm > 0:
        #                 if i == 0:
        #                     value = pwm
        #                 else:
        #                     value = -pwm
        #         self.set_property('M' + str(index + 1), value)
        #     else:
        #         for i in range(0, 2):
        #             actualIndex = (index * 2) + i
        #             pwm = self.txt.getPwm(actualIndex)
        #             self.set_property('O' + str(actualIndex + 1), pwm)

        self.capCams()

        # Update TXT state propeties
        self.set_property(
            'inputVoltage',
            self.txt.getPower() / 1000
        )
        self.set_property(
            'refVoltage',
            self.txt.getReferencePower() / 1000
        )
        self.set_property(
            'temperature',
            self.txt.getTemperature()
        )


if __name__ == '__main__':
    wotApplication(sys.argv)
