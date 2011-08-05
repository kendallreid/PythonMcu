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

import sys
import types

if __name__ == "__main__":
    # allow "PythonMcu" package imports when executing this module
    sys.path.append('../../')

from PythonMcu.Midi.MidiConnection import MidiConnection


class McuInterconnector(object):

    _LED_STATUS = {
        0x00: 'off',
        0x01: 'flashing',
        0x7F: 'on'
        }

    _MCU_COMMANDS = [
        'mute_channel_1',
        'mute_channel_2',
        'mute_channel_3',
        'mute_channel_4',
        'mute_channel_5',
        'mute_channel_6',
        'mute_channel_7',
        'mute_channel_8',
        'record_ready_channel_1',
        'record_ready_channel_2',
        'record_ready_channel_3',
        'record_ready_channel_4',
        'record_ready_channel_5',
        'record_ready_channel_6',
        'record_ready_channel_7',
        'record_ready_channel_8',
        'select_channel_1',
        'select_channel_2',
        'select_channel_3',
        'select_channel_4',
        'select_channel_5',
        'select_channel_6',
        'select_channel_7',
        'select_channel_8',
        'solo_channel_1',
        'solo_channel_2',
        'solo_channel_3',
        'solo_channel_4',
        'solo_channel_5',
        'solo_channel_6',
        'solo_channel_7',
        'solo_channel_8',

        'assignment_eq',
        'assignment_instrument',
        'assignment_pan_surround',
        'assignment_plug_in',
        'assignment_send',
        'assignment_track',
        'automation_latch',
        'automation_read_off',
        'automation_touch',
        'automation_trim',
        'automation_write',
        'beats',
        'click',
        'cycle',
        'drop',
        'fast_forward',
        'flip',
        'global_view',
        'group',
        'marker',
        'nudge',
        'play',
        'record',
        'relay_click',
        'replace',
        'rewind',
        'rude_solo',
        'scrub',
        'smpte',
        'solo',
        'stop',
        'utilities_save',
        'utilities_undo',
        'zoom'
    ]


    def __init__(self, mackie_host_control, hardware_controller):
        self._mackie_host_control = mackie_host_control
        self._hardware_controller = hardware_controller

        # set this here so the hardware controller can notify the user
        # about the connection process
        self._hardware_controller.set_mackie_host_control(self._mackie_host_control)
        self._mackie_host_control.set_hardware_controller(self)

        self._led__hardware_to_mcu = {}

        self._led__mcu_to_hardware = {}
        for command in self._MCU_COMMANDS:
            self._led__mcu_to_hardware[command] = { 'midi_control': None, 'value': 0 }

        # DEBUG
        self._debug = True

        self.link_controls('mute_channel_1', 'cc24')
        self.link_controls('mute_channel_2', 'cc25')
        self.link_controls('mute_channel_3', 'cc26')
        self.link_controls('mute_channel_4', 'cc27')
        self.link_controls('mute_channel_5', 'cc28')
        self.link_controls('mute_channel_6', 'cc29')
        self.link_controls('mute_channel_7', 'cc30')
        self.link_controls('mute_channel_8', 'cc31')

        self.link_controls('solo_channel_1', 'cc32')
        self.link_controls('solo_channel_2', 'cc33')
        self.link_controls('solo_channel_3', 'cc34')
        self.link_controls('solo_channel_4', 'cc35')
        self.link_controls('solo_channel_5', 'cc36')
        self.link_controls('solo_channel_6', 'cc37')
        self.link_controls('solo_channel_7', 'cc38')
        self.link_controls('solo_channel_8', 'cc39')


    def _log(self, message):
        print '[MCU Interconnector   ]  ' + message


    # --- MCU Interconnector commands ---

    def connect(self):
        self._hardware_controller.connect()
        self._mackie_host_control.connect()


    def disconnect(self):
        self._mackie_host_control.disconnect()
        self._hardware_controller.disconnect()


    def host_connected(self):
        self._hardware_controller.host_connected()


    def process_midi_input(self):
        self._hardware_controller.process_midi_input()
        self._mackie_host_control.process_midi_input()


    def link_controls(self, mcu_command, midi_control):
        self._led__hardware_to_mcu[midi_control] = mcu_command
        self._led__mcu_to_hardware[mcu_command]['midi_control'] = midi_control


    def unlink_controls(self, mcu_command, midi_control):
        del self._led__hardware_to_mcu[midi_control]
        self._led__mcu_to_hardware[mcu_command]['midi_control'] = None


    def _update_led(self, command, status):
        if self._led__mcu_to_hardware[command]['value'] != status:
            self._led__mcu_to_hardware[command]['value'] = status

            if self._led__mcu_to_hardware[command]['midi_control'] is not None:
                self._hardware_controller.update_led_2( \
                    self._led__mcu_to_hardware[command]['midi_control'], status)
            elif self._debug:
                self._log('LED "%s" NOT set to "%s".' % \
                              (command.upper(), self._LED_STATUS[status]))


    # --- Hardware Controller commands ---


    def has_display_7seg(self):
        return self._hardware_controller.has_display_7seg()


    def has_display_lcd(self):
        return self._hardware_controller.has_display_lcd()


    def has_display_timecode(self):
        return self._hardware_controller.has_display_timecode()


    def has_automated_faders(self):
        return self._hardware_controller.has_automated_faders()


    def has_meter_bridge(self):
        return self._hardware_controller.has_meter_bridge()


    # --- Mackie Control Unit commands ---

    def fader_moved(self, fader_id, fader_position):
        self._hardware_controller.fader_moved(fader_id, fader_position)


    def set_peak_level(self, meter_id, meter_level):
        self._hardware_controller.set_peak_level(meter_id, meter_level)


    def set_display_7seg(self, position, character_code):
        self._hardware_controller.set_display_7seg(position, character_code)


    def set_display_timecode(self, position, character_code):
        self._hardware_controller.set_display_timecode(position, character_code)


    def set_vpot_led_ring(self, vpot_id, vpot_center_led, \
                              vpot_mode, vpot_position):
        self._hardware_controller.set_vpot_led_ring( \
            vpot_id, vpot_center_led, vpot_mode, vpot_position)


    def update_lcd(self, position, new_string):
        """
        send string of maximum 72 bytes to controller LCD

        position 1: top row
        position 2: bottom row
        """
        self._hardware_controller.update_lcd(position, new_string)


    def update_led_channel_record_ready(self, channel, status):
        # channel: 0 - 7
        self._update_led('record_ready_channel_%d' % (channel + 1), status)


    def update_led_channel_solo(self, channel, status):
        # channel: 0 - 7
        self._update_led('solo_channel_%d' % (channel + 1), status)


    def update_led_channel_mute(self, channel, status):
        # channel: 0 - 7
        self._update_led('mute_channel_%d' % (channel + 1), status)


    def update_led_channel_select(self, channel, status):
        # channel: 0 - 7
        self._update_led('select_channel_%d' % (channel + 1), status)


    def update_led_assignment_track(self, status):
        self._update_led('assignment_track', status)


    def update_led_assignment_send(self, status):
        self._update_led('assignment_send', status)


    def update_led_assignment_pan_surround(self, status):
        self._update_led('assignment_pan_surround', status)


    def update_led_assignment_plug_in(self, status):
        self._update_led('assignment_plug_in', status)


    def update_led_assignment_eq(self, status):
        self._update_led('assignment_eq', status)


    def update_led_assignment_instrument(self, status):
        self._update_led('assignment_instrument', status)


    def update_led_flip(self, status):
        self._update_led('flip', status)


    def update_led_global_view(self, status):
        self._update_led('global_view', status)


    def update_led_automation_read_off(self, status):
        self._update_led('automation_read_off', status)


    def update_led_automation_write(self, status):
        self._update_led('automation_write', status)


    def update_led_automation_trim(self, status):
        self._update_led('automation_trim', status)


    def update_led_automation_touch(self, status):
        self._update_led('automation_touch', status)


    def update_led_automation_latch(self, status):
        self._update_led('automation_latch', status)


    def update_led_group(self, status):
        self._update_led('group', status)


    def update_led_utilities_save(self, status):
        self._update_led('utilities_save', status)


    def update_led_utilities_undo(self, status):
        self._update_led('utilities_undo', status)


    def update_led_marker(self, status):
        self._update_led('marker', status)


    def update_led_nudge(self, status):
        self._update_led('nudge', status)


    def update_led_cycle(self, status):
        self._update_led('cycle', status)


    def update_led_drop(self, status):
        self._update_led('drop', status)


    def update_led_replace(self, status):
        self._update_led('replace', status)


    def update_led_click(self, status):
        self._update_led('click', status)


    def update_led_solo(self, status):
        self._update_led('solo', status)


    def update_led_rewind(self, status):
        self._update_led('rewind', status)


    def update_led_fast_forward(self, status):
        self._update_led('fast_forward', status)


    def update_led_stop(self, status):
        self._update_led('stop', status)


    def update_led_play(self, status):
        self._update_led('play', status)


    def update_led_record(self, status):
        self._update_led('record', status)


    def update_led_zoom(self, status):
        self._update_led('zoom', status)


    def update_led_scrub(self, status):
        self._update_led('scrub', status)


    def update_led_smpte(self, status):
        self._update_led('smpte', status)


    def update_led_beats(self, status):
        self._update_led('beats', status)


    def update_led_rude_solo(self, status):
        self._update_led('rude_solo', status)


    def update_led_relay_click(self, status):
        self._update_led('relay_click', status)