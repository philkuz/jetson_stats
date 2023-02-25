# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import curses
from .jtopgui import Page
# Graphics elements
from .lib.common import unit_to_string
# Graphic library
from .lib.colors import NColors
from .lib.chart import Chart
from .lib.smallbutton import SmallButton, ButtonList

FAN_STEP = 10
PROFILE_STR = "Profiles:"
TEMPERATURE_MAX = 84
TEMPERATURE_CRIT = 100


def compact_temperatures(stdscr, pos_y, pos_x, width, height, jetson):
    counter = 0
    center_x = pos_x + width // 2 + 1
    offset = 2
    # Plot title
    stdscr.addstr(pos_y, center_x - offset - 10, " [Sensor] ", curses.A_BOLD)
    stdscr.addstr(pos_y, center_x + offset, " [Temp] ", curses.A_BOLD)
    # Plot name and temperatures
    for idx, (name, sensor) in enumerate(jetson.temperature.items()):
        # Print temperature name
        temperature = sensor['temp']
        # Set color temperature
        max_value = sensor['max'] if 'max' in sensor else TEMPERATURE_MAX
        crit_value = sensor['crit'] if 'crit' in sensor else TEMPERATURE_CRIT
        # Set color
        color = curses.A_NORMAL
        if temperature >= crit_value:
            color = NColors.red()
        elif temperature >= max_value:
            color = NColors.yellow()
        # Print temperature value
        try:
            stdscr.addstr(pos_y + idx + 1, center_x - offset - 9, name)
            stdscr.addstr(pos_y + idx + 1, center_x + offset + 1, ("{val:3.2f}C").format(val=temperature), color)
        except curses.error:
            break
        counter = idx
    return counter


def compact_power(stdscr, pos_y, pos_x, width, height, jetson):
    LIMIT = 25
    # center_x = pos_x + width // 2 if width > LIMIT else pos_x + width // 2 + 4
    center_x = pos_x + width // 2 + 2 if width > LIMIT else pos_x + width // 2 + 6
    column_power = 9
    # Plot title
    stdscr.addstr(pos_y, center_x - column_power - 5, " [Power] ", curses.A_BOLD)
    stdscr.addstr(pos_y, center_x - 3, " [Inst] ", curses.A_BOLD)
    if width > LIMIT:
        stdscr.addstr(pos_y, center_x + column_power - 4, " [Avg] ", curses.A_BOLD)
    # Plot watts
    power = jetson.power['rail']
    for idx, name in enumerate(power):
        value = power[name]
        string_name = name.replace("VDDQ_", "").replace("VDD_", "").replace("_", " ")
        stdscr.addstr(pos_y + idx + 1, center_x - column_power - 5, string_name, curses.A_NORMAL)
        unit_power = unit_to_string(value['power'], value['unit'], 'W')
        stdscr.addstr(pos_y + idx + 1, center_x - 1, unit_power, curses.A_NORMAL)
        if width > LIMIT:
            unit_avg = unit_to_string(value['avg'], value['unit'], 'W')
            stdscr.addstr(pos_y + idx + 1, center_x + column_power - 3, unit_avg, curses.A_NORMAL)
    # Plot totals before finishing
    total = jetson.power['tot']
    len_power = len(power)
    stdscr.addstr(pos_y + len_power + 1, center_x - column_power - 5, 'ALL', curses.A_BOLD)
    unit_power = unit_to_string(total['power'], total['unit'], 'W')
    stdscr.addstr(pos_y + len_power + 1, center_x - 1, unit_power, curses.A_BOLD)
    if width > LIMIT:
        unit_avg = unit_to_string(total['avg'], total['unit'], 'W')
        stdscr.addstr(pos_y + len_power + 1, center_x + column_power - 3, unit_avg, curses.A_BOLD)
    return len(power) + 1


class CTRL(Page):

    def __init__(self, stdscr, jetson):
        super(CTRL, self).__init__("CTRL", stdscr, jetson)
        # Only if exist a fan will be load a chart
        # Initialize FAN chart
        self._fan_gui = {}
        for fan_name in self.jetson.fan:
            fan = self.jetson.fan[fan_name]
            # Initialize profile and list of fan
            profiles = jetson.fan.all_profiles(fan_name)
            button_list = ButtonList(stdscr, self.action_fan_profile, profiles, info={'name': fan_name})
            size_profile = max([len(profile) for profile in profiles] + [len(PROFILE_STR)]) + 2
            self._fan_gui[fan_name] = {'profile': button_list, 'fan': [], 'size_w': size_profile, 'len_profiles': len(profiles)}
            # Initialize all fan chart and buttons
            for idx in range(len(fan['speed'])):
                chart_fan = Chart(jetson, "{name} {idx}".format(name=fan_name.upper(), idx=idx), self.update_chart,
                                  line="o", color_text=curses.COLOR_CYAN, color_chart=[curses.COLOR_CYAN])
                button_increase = SmallButton(stdscr, self.action_fan_increase, info={'name': fan_name, 'idx': idx})
                button_decrease = SmallButton(stdscr, self.action_fan_decrease, info={'name': fan_name, 'idx': idx})
                self._fan_gui[fan_name]['fan'] += [{'chart': chart_fan, 'increase': button_increase, 'decrease': button_decrease}]
        # Initialize jetson_clocks buttons
        if self.jetson.jetson_clocks is not None:
            self._jetson_clocks_start = SmallButton(stdscr, self.action_jetson_clocks_start, trigger_key='s')
            self._jetson_clocks_boot = SmallButton(stdscr, self.action_jetson_clocks_boot, trigger_key='e')
        # Initialize NVP Model buttons
        if self.jetson.nvpmodel is not None:
            self._nvp_default = self.jetson.nvpmodel.get_default()
            # nvp_modes = [name.replace('MODE_', '').replace('_', ' ') for name in self.jetson.nvpmodel.modes]
            self._nvpmodel_profile = ButtonList(stdscr, self.action_nvpmodels, self.jetson.nvpmodel.models)
            self._nvpmodel_increase = SmallButton(stdscr, self.action_nvp_increase, trigger_key='+')
            self._nvpmodel_decrease = SmallButton(stdscr, self.action_nvp_decrease, trigger_key='-')

    def action_fan_profile(self, info, selected):
        # Set new fan profile
        self.jetson.fan.set_profile(info['name'], info['label'])

    def action_fan_increase(self, info, selected):
        # Read current speed
        speed = self.jetson.fan.get_speed(info['name'], info['idx'])
        # Round and increase speed
        spd = round(speed / 10) * 10 + FAN_STEP
        new_speed = spd if spd <= 100 else 100
        # Update fan speed
        self.jetson.fan.set_speed(info['name'], new_speed, info['idx'])

    def action_fan_decrease(self, info, selected):
        # Read current speed
        speed = self.jetson.fan.get_speed(info['name'], info['idx'])
        # Round and decrease speed
        spd = round(speed / 10) * 10 - FAN_STEP
        new_speed = spd if spd >= 0 else 0
        # Update fan speed
        self.jetson.fan.set_speed(info['name'], new_speed, info['idx'])

    def action_jetson_clocks_start(self, info, selected):
        # Start jetson_clocks
        self.jetson.jetson_clocks = not self.jetson.jetson_clocks

    def action_jetson_clocks_boot(self, info, selected):
        # Start jetson_clocks
        self.jetson.jetson_clocks.boot = not self.jetson.jetson_clocks.boot

    def action_nvpmodels(self, info, selected):
        # Set new nvpmodel
        self.jetson.nvpmodel = info['label']

    def action_nvp_increase(self, info, selected):
        # NVPmodel controller
        if self.jetson.nvpmodel.id >= len(self.jetson.nvpmodel.models) - 1:
            return
        self.jetson.nvpmodel += 1

    def action_nvp_decrease(self, info, selected):
        # NVPmodel controller
        if self.jetson.nvpmodel.id <= 0:
            return
        self.jetson.nvpmodel -= 1

    def update_chart(self, jetson, name):
        info_chart = name.split(" ")
        name = info_chart[0].lower()
        idx = int(info_chart[1])
        speed = jetson.fan[name]['speed'][idx]
        # Append in list
        return {
            'value': [speed],
        }

    def control_jetson_clocks(self, pos_y, pos_x, key, mouse):
        # Show jetson_clocks
        self.stdscr.addstr(pos_y, pos_x, "Jetson Clocks:", curses.A_BOLD)
        # Status jetson clocks
        jetson_clocks_status = self.jetson.jetson_clocks.status
        # Color status
        if jetson_clocks_status == "running":
            color = (curses.A_BOLD | NColors.green())  # Running (Bold)
        elif jetson_clocks_status == "inactive":
            color = curses.A_NORMAL       # Normal (Grey)
        elif "ing" in jetson_clocks_status:
            color = NColors.yellow()  # Warning (Yellow)
        else:
            color = NColors.red()  # Error (Red)
        # Draw status button
        self._jetson_clocks_start.update(pos_y, pos_x + 15, jetson_clocks_status, key, mouse, color=color)
        # Draw boot button
        boot = self.jetson.jetson_clocks.boot
        jetson_clocks_boot = "enable" if boot else "disable"
        self.stdscr.addstr(pos_y, pos_x + 31, "on boot:", curses.A_BOLD)
        color_boot = NColors.green() if boot else curses.A_NORMAL
        self._jetson_clocks_boot.update(pos_y, pos_x + 40, jetson_clocks_boot, key, mouse, color=color_boot)

    def control_nvpmodes(self, pos_y, pos_x, key, mouse):
        # Draw all profiles
        self.stdscr.addstr(pos_y, pos_x, "NVP modes:", curses.A_BOLD)
        # Write ID NVP model
        id = self.jetson.nvpmodel.id
        color = NColors.yellow() if self.jetson.nvpmodel.is_running() else curses.A_BOLD
        self.stdscr.addstr(pos_y, pos_x + 16, str(id), color)
        # Add buttons -/+
        self._nvpmodel_decrease.update(pos_y, pos_x + 11, key=key, mouse=mouse)
        self._nvpmodel_increase.update(pos_y, pos_x + 18, key=key, mouse=mouse)
        # Draw all modes
        current_mode = self.jetson.nvpmodel.name
        colors = [curses.A_NORMAL if status else NColors.red() for status in self.jetson.nvpmodel.status]
        self._nvpmodel_profile.update(pos_y + 1, pos_x + 2, key, mouse, current_mode, colors)
        # Write letter D for default
        self.stdscr.addstr(pos_y + self._nvp_default['id'] + 1, pos_x, "D", curses.A_BOLD)

    def control_power(self, pos_y, pos_x, key, mouse):
        if not self.jetson.power:
            return
        # Width  table
        width = 53
        # Draw all power
        power = self.jetson.power['rail']
        # Draw head table
        self.stdscr.addch(pos_y, pos_x, curses.ACS_ULCORNER)
        self.stdscr.addch(pos_y, pos_x + width - 1, curses.ACS_URCORNER)
        self.stdscr.hline(pos_y, pos_x + 1, curses.ACS_HLINE, width - 2)
        self.stdscr.addstr(pos_y, pos_x + 5, " Power ", curses.A_BOLD)
        # Draw header table
        self.stdscr.addstr(pos_y + 1, pos_x, "[Name]", curses.A_BOLD)
        self.stdscr.addstr(pos_y + 1, pos_x + 18, "[Power]", curses.A_BOLD)
        self.stdscr.addstr(pos_y + 1, pos_x + 26, "[Volt]", curses.A_BOLD)
        self.stdscr.addstr(pos_y + 1, pos_x + 33, "[Curr]", curses.A_BOLD)
        self.stdscr.addstr(pos_y + 1, pos_x + 40, "[Warn]", curses.A_BOLD)
        self.stdscr.addstr(pos_y + 1, pos_x + 47, "[Crit]", curses.A_BOLD)
        # Draw all values
        pos_y_table = pos_y + 2
        for idx, name in enumerate(power):
            value = power[name]
            self.stdscr.addstr(pos_y_table + idx, pos_x, name, curses.A_NORMAL)
            # Convert all values in readable strings
            unit_volt = unit_to_string(value['volt'], value['unit'], 'V')
            unit_curr = unit_to_string(value['curr'], value['unit'], 'A')
            unit_power = unit_to_string(value['power'], value['unit'], 'W')
            # Print all values
            self.stdscr.addstr(pos_y_table + idx, pos_x + 18, unit_power, curses.A_NORMAL)
            self.stdscr.addstr(pos_y_table + idx, pos_x + 26, unit_volt, curses.A_NORMAL)
            self.stdscr.addstr(pos_y_table + idx, pos_x + 33, unit_curr, curses.A_NORMAL)
            if 'warn' in value:
                unit_curr_warn = unit_to_string(value['warn'], value['unit'], 'A')
                self.stdscr.addstr(pos_y_table + idx, pos_x + 40, unit_curr_warn, curses.A_NORMAL)
            if 'crit' in value:
                unit_curr_crit = unit_to_string(value['crit'], value['unit'], 'A')
                self.stdscr.addstr(pos_y_table + idx, pos_x + 47, unit_curr_crit, curses.A_NORMAL)
        # Draw total power
        total = self.jetson.power['tot']
        len_power = len(power)
        self.stdscr.addstr(pos_y_table + len_power, pos_x, 'ALL', curses.A_BOLD)
        unit_power_total = unit_to_string(total['power'], total['unit'], 'W')
        self.stdscr.addstr(pos_y_table + len_power, pos_x + 18, unit_power_total, curses.A_BOLD)

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Measure height
        fan_height = (height * 1 // 3 + 2) // len(self.jetson.fan) if len(self.jetson.fan) > 0 else 0
        # Draw all GPU
        for fan_idx, (fan_gui, fan_name) in enumerate(zip(self._fan_gui, self.jetson.fan)):
            gui_chart = self._fan_gui[fan_gui]
            fan = self.jetson.fan[fan_name]
            num_fans = len(fan['speed'])
            # Print all profiles
            pos_y_profiles = fan_height // 2 - gui_chart['len_profiles']
            size_profile = gui_chart['size_w']
            self.stdscr.addstr(first + 1 + fan_idx * (fan_height + 1) + pos_y_profiles - 1, 1, PROFILE_STR, curses.A_BOLD)
            # Split width for each pwm
            fan_speed_width = (width - size_profile - 6) // num_fans
            # Draw a button list with all profiles
            profile = self.jetson.fan.get_profile(fan_name)
            gui_chart['profile'].update(first + 1 + fan_idx * (fan_height + 1) + pos_y_profiles, 1, key, mouse, profile)
            # Print all fans
            for idx, speed in enumerate(fan['speed']):
                # Set size chart gpu
                size_x = [size_profile + idx * fan_speed_width, size_profile + (idx + 1) * (fan_speed_width - 1)]
                size_y = [first + 1 + fan_idx * (fan_height + 1), first + 1 + (fan_idx + 1) * (fan_height - 1)]
                # Print speed and RPM
                label_fan = "PWM {speed: >3.0f}%".format(speed=speed)
                if 'rpm' in fan:
                    label_fan += " - {rpm}RPM".format(rpm=fan['rpm'][idx])
                # Draw GPU chart
                gui_chart['fan'][idx]['chart'].draw(self.stdscr, size_x, size_y, label=label_fan, y_label=False)
                # Draw speed buttons
                pos_x_control_fan = (fan_speed_width - 6) // 2
                if fan_speed_width > 40:
                    self.stdscr.addstr(first + 1 + fan_idx * (fan_height + 1),
                                       size_profile + idx * fan_speed_width + pos_x_control_fan + 4,
                                       "Speed", curses.A_BOLD)
                gui_chart['fan'][idx]['decrease'].update(first + 1 + fan_idx * (fan_height + 1),
                                                         size_profile + idx * fan_speed_width + pos_x_control_fan + 10,
                                                         '-', key, mouse)
                gui_chart['fan'][idx]['increase'].update(first + 1 + fan_idx * (fan_height + 1),
                                                         size_profile + idx * fan_speed_width + pos_x_control_fan + 14,
                                                         '-', key, mouse)
            # Plot y axis
            gui_chart['fan'][0]['chart'].draw_y_axis(self.stdscr,
                                                     first + 1 + fan_idx * (fan_height + 1),
                                                     size_profile + num_fans * (fan_speed_width - 1) + 1,
                                                     fan_height - 1)
        # Draw jetson clocks
        line_counter = fan_height
        if self.jetson.jetson_clocks is not None:
            self.control_jetson_clocks(first + 1 + line_counter, 1, key, mouse)
            line_counter += 1
        # Draw nvpmodels
        width_spacing = 5
        if self.jetson.nvpmodel is not None:
            self.control_nvpmodes(first + 1 + line_counter, 1, key, mouse)
            width_spacing = width // 2 - 16
        # Draw all power info
        self.control_power(first + 1 + line_counter, width_spacing, key, mouse)
# EOF
