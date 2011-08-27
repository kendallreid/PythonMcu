#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PythonMcu
=========
Mackie Host Controller written in Python

Copyright (c) 2011 Martin Zuther (http://www.mzuther.de/)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Thank you for using free software!

"""

from PythonMcu.Hardware import *
from PythonMcu.MackieControl.MackieHostControl import MackieHostControl
from PythonMcu.McuInterconnector.McuInterconnector import McuInterconnector
from PythonMcu.Midi.MidiConnection import MidiConnection
from PythonMcu.Tools.ApplicationSettings import *

import platform
import sys

import pygame.version
import PySide
from PySide.QtCore import *
from PySide.QtGui import *


configuration = ApplicationSettings()


def callback_log(message):
    print message


class PythonMcu(QFrame):
    def __init__(self, parent=None):
        super(PythonMcu, self).__init__(parent)

        # must be defined before reading the configuration file!
        self._edit_usage_hint = QTextEdit()
        self._edit_usage_hint.setReadOnly(True)

        font = QFont()
        font.setStyleHint(QFont.TypeWriter, QFont.PreferAntialias)
        self._edit_usage_hint.setFontFamily(font.defaultFamily())

        self._read_configuration()

        self._timer = None
        self._interconnector = None

        icon = self.style().standardIcon(QStyle.SP_TitleBarMenuButton)
        self.setWindowIcon(icon)

        mcu_model_ids = ['Logic Control', 'Logic Control XT', \
                              'Mackie Control', 'Mackie Control XT']

        hardware_controllers = [ \
            'Novation ZeRO SL MkII', \
            'Novation ZeRO SL MkII (MIDI)'
        ]

        # get version number of "Python MCU"
        version = configuration.get_application_information('version')
        self.setWindowTitle('Python MCU ' + version)

        # create layouts and add widgets
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.frame_mcu = QFrame()
        self.frame_mcu.setFrameStyle(QFrame.StyledPanel)
        self.frame_mcu.setFrameShadow(QFrame.Raised)
        self.layout.addWidget(self.frame_mcu)
        self.grid_layout_mcu = QGridLayout()
        self.frame_mcu.setLayout(self.grid_layout_mcu)

        self.frame_controller = QFrame()
        self.frame_controller.setFrameStyle(QFrame.StyledPanel)
        self.frame_controller.setFrameShadow(QFrame.Raised)
        self.layout.addWidget(self.frame_controller)
        self.grid_layout_controller = QGridLayout()
        self.frame_controller.setLayout(self.grid_layout_controller)


        self._combo_mcu_model_id = self._create_combo_box( \
            self.grid_layout_mcu, self._emulated_mcu_model, \
                'MCU model:', mcu_model_ids)

        self._checkbox_use_challenge_response = QCheckBox()
        self._checkbox_use_challenge_response.setText('Use ch&allenge response')

        if self._use_challenge_response:
            self._checkbox_use_challenge_response.setCheckState(Qt.Checked)
        else:
            self._checkbox_use_challenge_response.setCheckState(Qt.Unchecked)

        self.grid_layout_mcu.addWidget(self._checkbox_use_challenge_response, \
                                           self.grid_layout_mcu.rowCount(), 1)
        self._checkbox_use_challenge_response.stateChanged.connect( \
            (self.checkbox_state_changed))

        self._combo_mcu_midi_input = self._create_combo_box( \
            self.grid_layout_mcu, self._sequencer_midi_input, \
                'MIDI In:', MidiConnection.get_midi_inputs(), )

        self._combo_mcu_midi_output = self._create_combo_box( \
            self.grid_layout_mcu, self._sequencer_midi_output, \
                'MIDI Out:', MidiConnection.get_midi_outputs())


        self._combo_hardware_controller = self._create_combo_box( \
            self.grid_layout_controller, self._hardware_controller, \
                'Controller:', hardware_controllers)

        self._combo_controller_midi_input = self._create_combo_box( \
            self.grid_layout_controller, self._controller_midi_input, \
                'MIDI In:', MidiConnection.get_midi_inputs())

        self._combo_controller_midi_output = self._create_combo_box( \
            self.grid_layout_controller, self._controller_midi_output, \
                'MIDI Out:', MidiConnection.get_midi_outputs())

        self.grid_layout_controller.addWidget( \
            self._edit_usage_hint, self.grid_layout_controller.rowCount(), \
                0, 1, 2)

        self.bottom_layout = QHBoxLayout()
        self.layout.addLayout(self.bottom_layout)

        self.button_start_stop = QPushButton('&Start')
        self.bottom_layout.addWidget(self.button_start_stop)
        self.button_start_stop.setDefault(True)
        self.button_start_stop.clicked.connect(self.interconnector_start_stop)

        self.button_close = QPushButton('&Close')
        self.bottom_layout.addWidget(self.button_close)
        self.button_close.clicked.connect(self.close_application)

        self.button_license = QPushButton('&License')
        self.bottom_layout.addWidget(self.button_license)
        self.button_license.clicked.connect(self.display_license)

        self._timer = QTimer(self)
        self._timer.setInterval(int(self._midi_latency))
        self._timer.timeout.connect(self.process_midi_input)


    def _read_configuration(self):
        # initialise defaults for MCU and hardware controller
        emulated_mcu_model_default = MackieHostControl.get_preferred_mcu_model()
        hardware_controller_default = 'Novation ZeRO SL MkII'
        midi_latency_default = '1'

        # retrieve user configuration for MCU and hardware controller
        self._emulated_mcu_model = configuration.get_option( \
            'Python MCU', 'emulated_mcu_model', emulated_mcu_model_default)
        self._hardware_controller = configuration.get_option( \
            'Python MCU', 'hardware_controller', hardware_controller_default)
        self._midi_latency = configuration.get_option( \
            'Python MCU', 'midi_latency', midi_latency_default)

        # calculate MCU model ID from its name
        self._mcu_model_id = MackieHostControl.get_mcu_id_from_model( \
            self._emulated_mcu_model)

        # Logic Control units use MCU challenge-response by default, ...
        if self._mcu_model_id in [0x10, 0x11]:
            use_challenge_response_default = True
        # whereas Mackie Control Units don't seem to use it
        else:
            use_challenge_response_default = False

        if configuration.get_option( \
            'Python MCU', 'use_challenge_response', \
                use_challenge_response_default) == 'True':
            self._use_challenge_response = True
        else:
            self._use_challenge_response = False

        # get preferred MIDI ports for hardware controller
        (controller_midi_input_default, controller_midi_output_default) = \
            self._initialise_hardware_controller()

        # initialise MIDI port defaults for MCU and hardware
        # controller
        sequencer_midi_input_default = \
            MackieHostControl.get_preferred_midi_input()
        sequencer_midi_output_default = \
            MackieHostControl.get_preferred_midi_output()

        # retrieve user configuration for MCU's MIDI ports
        self._sequencer_midi_input = configuration.get_option( \
            'Python MCU', 'sequencer_midi_input', \
                sequencer_midi_input_default)
        self._sequencer_midi_output = configuration.get_option( \
            'Python MCU', 'sequencer_midi_output', \
                sequencer_midi_output_default)

        # retrieve user configuration for hardware controller's MIDI
        # ports
        self._controller_midi_input = configuration.get_option( \
            'Python MCU', 'controller_midi_input', \
                controller_midi_input_default)
        self._controller_midi_output = configuration.get_option( \
            'Python MCU', 'controller_midi_output', \
                controller_midi_output_default)


    def _create_combo_box(self, layout, selection, label_text, choices):
        row = layout.rowCount()

        label = QLabel(None)
        label.setText(label_text)
        layout.addWidget(label, row, 0)

        widget = QComboBox()
        layout.addWidget(widget, row, 1)

        choices.sort()
        widget.addItems(choices)

        current_index = widget.findText(selection)
        widget.setCurrentIndex(current_index)
        widget.currentIndexChanged.connect(self.combobox_item_selected)

        return widget


    def _initialise_hardware_controller(self):
        # the hardware controller's class name is simply the
        # controller's manufacturer and name with all spaces converted
        # to underscores and all brackets removed
        self._hardware_controller_class = \
            self._hardware_controller.replace(' ', '_')
        self._hardware_controller_class = \
            self._hardware_controller_class.replace('(', '').replace(')', '')
        self._hardware_controller_class = \
            self._hardware_controller_class.replace('[', '').replace(']', '')
        self._hardware_controller_class = \
            self._hardware_controller_class.replace('{', '').replace('}', '')

        # get hardware controller's preferred MIDI ports
        eval_controller_midi_input = \
            '{0!s}.{0!s}.get_preferred_midi_input()'.format( \
            self._hardware_controller_class)
        eval_controller_midi_output = \
            '{0!s}.{0!s}.get_preferred_midi_output()'.format( \
            self._hardware_controller_class)

        controller_midi_input_default = eval(eval_controller_midi_input)
        controller_midi_output_default = eval(eval_controller_midi_output)

        # show controller's usage hint
        usage_hint = '{0!s}.{0!s}.get_usage_hint()'.format( \
            self._hardware_controller_class)
        self._edit_usage_hint.setText(eval(usage_hint))

        return (controller_midi_input_default, controller_midi_output_default)


    def combobox_item_selected(self, selected_text):
        widget = self.sender()

        if widget == self._combo_mcu_model_id:
            self._emulated_mcu_model = selected_text
            configuration.set_option( \
                'Python MCU', 'emulated_mcu_model', \
                    self._emulated_mcu_model)

            if self._emulated_mcu_model.startswith('Logic'):
                self._checkbox_use_challenge_response.setCheckState(Qt.Checked)
            else:
                self._checkbox_use_challenge_response.setCheckState( \
                    Qt.Unchecked)

        elif widget == self._combo_mcu_midi_input:
            self._sequencer_midi_input = selected_text
            configuration.set_option( \
                'Python MCU', 'sequencer_midi_input', \
                    self._sequencer_midi_input)
        elif widget == self._combo_mcu_midi_output:
            self._sequencer_midi_output = selected_text
            configuration.set_option( \
                'Python MCU', 'sequencer_midi_output', \
                    self._sequencer_midi_output)
        elif widget == self._combo_hardware_controller:
            self._hardware_controller = selected_text
            configuration.set_option( \
            'Python MCU', 'hardware_controller', \
                self._hardware_controller)

            # get preferred MIDI ports for hardware controller
            (controller_midi_input_default, controller_midi_output_default) = \
                self._initialise_hardware_controller()

            # update hardware controller's MIDI ports in GUI
            current_index = self._combo_controller_midi_input.findText( \
                controller_midi_input_default)
            self._combo_controller_midi_input.setCurrentIndex(current_index)

            current_index = self._combo_controller_midi_output.findText( \
                controller_midi_output_default)
            self._combo_controller_midi_output.setCurrentIndex(current_index)
        elif widget == self._combo_controller_midi_input:
            self._controller_midi_input = selected_text
            configuration.set_option( \
                'Python MCU', 'controller_midi_input', \
                    self._controller_midi_input)
        elif widget == self._combo_controller_midi_output:
            self._controller_midi_output = selected_text
            configuration.set_option( \
                'Python MCU', 'controller_midi_output', \
                    self._controller_midi_output)
        else:
            callback_log('QComboBox not handled ("%s").' % selected_text)


    def checkbox_state_changed(self, state):
        widget = self.sender()

        if widget == self._checkbox_use_challenge_response:
            self._use_challenge_response = widget.isChecked()

            configuration.set_option( \
            'Python MCU', 'use_challenge_response', \
                self._use_challenge_response)
        else:
            callback_log('QCheckBox not handled ("%d").' % state)


    def process_midi_input(self):
        self._interconnector.process_midi_input()


    def display_license(self):
        pass


    def interconnector_start_stop(self):
        if not self._interconnector:
            self.button_start_stop.setText('&Stop')

            callback_log('Settings')
            callback_log('========')
            callback_log('Emulated MCU model:      %s' % \
                             self._emulated_mcu_model)
            callback_log('Use challenge-response:  %s' % \
                             self._use_challenge_response)
            callback_log('Sequencer MIDI input:    %s' % \
                             self._sequencer_midi_input)
            callback_log('Sequencer MIDI output:   %s' % \
                             self._sequencer_midi_output)
            callback_log('')
            callback_log('Hardware controller:     %s' % \
                             self._hardware_controller)
            callback_log('Controller MIDI input:   %s' % \
                             self._controller_midi_input)
            callback_log('Controller MIDI output:  %s' % \
                             self._controller_midi_output)
            callback_log('')
            callback_log('MIDI latency:            %s ms' % \
                             self._midi_latency)
            callback_log('')
            callback_log('')

            if configuration.has_changed():
                callback_log('Saving configuration file ...')
                configuration.save_configuration()

            callback_log('Starting MCU emulation...')
            callback_log('')

            # the "interconnector" is the brain of this application -- it
            # interconnects Mackie Control Host and MIDI controller while
            # handling the complete MIDI translation between those two
            self._interconnector = McuInterconnector( \
                self._mcu_model_id, \
                    self._use_challenge_response, \
                    self._sequencer_midi_input, \
                    self._sequencer_midi_output, \
                    self._hardware_controller_class, \
                    self._controller_midi_input, \
                    self._controller_midi_output, \
                    callback_log)
            self._interconnector.connect()

            self._timer.start()
        else:
            self.button_start_stop.setText('&Start')
            self._interconnector_stop()


    def _interconnector_stop(self):
            self._timer.stop()

            callback_log('')
            callback_log('Stopping MCU emulation...')
            callback_log('')

            self._interconnector.disconnect()
            self._interconnector = None

            callback_log('')


    def close_application(self):
        self.close()


    def closeEvent(self, event):
        if self._interconnector:
            self._interconnector_stop()

        callback_log('Exiting application...')
        callback_log('')


if __name__ == '__main__':
    callback_log('')
    callback_log(configuration.get_full_description())
    callback_log('')
    callback_log('')
    callback_log('Version numbers')
    callback_log('===============')
    callback_log('Python:  %s (%s)' % (platform.python_version(), \
                                           platform.python_implementation()))
    callback_log('PySide:  %s' % PySide.__version__)
    callback_log('pygame:  %s' % pygame.version.ver)
    callback_log('')
    callback_log('')

    # Create the Qt Application
    app = QApplication(sys.argv)

    # Create and show the form
    python_mcu = PythonMcu()
    python_mcu.show()

    # Run the main Qt loop
    sys.exit(app.exec_())
