# Copyright 2016-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""
This module contains the object classes for the different types of menu items, such as those that represent a
configurable module and those that represent the matching parameters.

Functions:
    None

Classes:
    MenuItem: base representation of a terminal (leaf) menu item.
    ToggleItem: representation of a terminal (leaf) menu item which can be toggled on and off.
    TextEntryItem: representation of a terminal (leaf) menu item that prompts the user for input when selected
    ExitItem: Representation of a terminal (leaf) menu item that performs no function itself, but the type can be used
    to infer the menu should exit when the item is selected.
    RunItem: representation of a terminal (leaf) menu item that indicates whether the configuration will be run upon
    exiting the menu.

Exceptions:
    MenuItemError: base error class for this module.
    MenuItemMissingValueError: raised when the call to instantiation a class is missing an argument..
"""
import curses

import ec2rlcore.menu_textpad_mod


class MenuItem(object):
    """
    Base representation of a terminal (leaf) menu item.

    Attributes:
        row_left (str): name of the item
        row_right (str): string representing this item on its parent menu
        header (str): header message displayed above the scrolling, selectable items
        helptext (str): explanatory help message for this item
    """

    def __init__(self,
                 row_left=None,
                 row_right="",
                 header=None,
                 helptext=None):
        if not row_left:
            raise MenuItemMissingValueError("row_left")
        if not header:
            raise MenuItemMissingValueError("header")
        if not helptext:
            raise MenuItemMissingValueError("helptext")

        self.row_left = row_left
        self.row_right = row_right
        self.header = header
        self.helptext = "{}\n\n{}".format(header, helptext)

    def __str__(self):
        return "    " + self.row_left

    # Support for printing with str.format()
    def __format__(self, *args, **kwargs):
        return " ".join((self.row_left, self.row_right))

    def __add__(self, other):
        return str(self) + other

    def __radd__(self, other):
        return other + str(self)

    def __call__(self):
        raise NotImplementedError("Method unimplemented in base MenuItem class.")

    def get_value(self):
        raise NotImplementedError("Method unimplemented in base MenuItem class.")


class ToggleItem(MenuItem):
    """
    Representation of a terminal (leaf) menu item that can be toggled on and off. e.g. "[*]" and "[ ]"

    Attributes:
        row_left (str): name of the item the user can toggle on/off
        header (str): header message displayed above the scrolling, selectable items
        helptext (str): explanatory help message for this item
        toggled (bool): represents whether the item is currently toggled on e.g. [*] not [ ]
    """
    def __init__(self,
                 row_left=None,
                 header=None,
                 helptext=None,
                 toggled=True):
        super(ToggleItem, self).__init__(row_left=row_left, header=header, helptext=helptext)
        self.toggled = toggled

    def __str__(self):
        return "[*] " + self.row_left if self.toggled else "[ ] " + self.row_left

    def __call__(self):
        self.toggled = not self.toggled

    def get_value(self):
        return str(self.toggled)


class TextEntryItem(MenuItem):
    """
    Representation of a terminal (leaf) menu item that prompts the user for input when selected.

    Attributes:
        row_left (str): name of the item whose value the user can enter
        row_right (str): the user-entered value of this object
        header (str): header message displayed above the scrolling, selectable items
        helptext (str): explanatory help message for this item
        message (str): the message displayed to the user in the Textbox window
    """
    def __init__(self,
                 row_left=None,
                 row_right="",
                 header="",
                 helptext=None,
                 message=""):
        super(TextEntryItem, self).__init__(row_left=row_left, row_right=row_right, header=header, helptext=helptext)
        self.message = message

    def __call__(self):
        self.row_right = curses.wrapper(self._draw_input, self.header, self.message).strip()

    def get_value(self):
        return self.row_right

    def _draw_input(self, stdscr, header, message):
        """
        Draw an input window with the provided message.

        Parameters:
            stdscr (WindowObject): the screen; handled by curses.wrapper
            header (str): header message displayed above the text entry box
            message (str): the message to the user displayed between the header and the text entry

        Returns:
            (Textbox): the Textbox's edit() returns a string representing the user's input
        """
        stdscr.clear()

        # Setup the title
        stdscr.addstr("ec2rl module configurator", curses.A_REVERSE)
        stdscr.chgat(-1, curses.A_REVERSE)
        curses.curs_set(0)

        num_columns = 30
        num_lines = 1
        uly = 3
        ulx = 3

        main_window = curses.newwin(curses.LINES - 1, curses.COLS, 1, 0)
        screen = main_window.subwin(curses.LINES - 7, curses.COLS - 4, 4, 2)

        # Setup background colors
        main_window.bkgd(" ", curses.color_pair(1))
        screen.bkgd(" ", curses.color_pair(2))

        # Draw borders around the screen subwindow
        screen.box()

        input_screen = main_window.subwin(num_lines, num_columns, uly + 5, ulx + 3)
        ec2rlcore.menu_textpad_mod.rectangle(screen, uly, ulx, uly + 1 + num_lines, ulx + 1 + num_columns)
        screen.addstr(1, 2, header, curses.A_UNDERLINE)
        # Truncate the string, if needed
        display_str = message[:curses.COLS - 10]
        screen.addstr(2, 5, display_str)

        # Draw the pieces of the overall screen (order matters)
        stdscr.refresh()
        main_window.noutrefresh()
        screen.noutrefresh()
        input_screen.noutrefresh()
        stdscr.noutrefresh()
        curses.doupdate()

        return ec2rlcore.menu_textpad_mod.Textbox(input_screen, bkgd_color=curses.color_pair(2)).edit()


class ExitItem(MenuItem):
    """
    Representation of a terminal (leaf) menu item that performs no function itself, but the type can be used to infer
    the menu should exit when the item is selected.

    Attributes:
        row_left (str): name of the item
        row_right (str): string representing this item on its parent menu
        header (str): message displayed above the selectable items in the list attribute
        helptext (str): explanatory help message for this item
    """
    def __init__(self,
                 row_left="Exit",
                 row_right="",
                 header=None,
                 helptext=None):
        super(ExitItem, self).__init__(row_left=row_left, row_right=row_right, header=header, helptext=helptext)

    def __call__(self):
        pass

    def get_value(self):
        return None


class RunItem(MenuItem):
    """
    Representation of a terminal (leaf) menu item that indicates whether the configuration will be run upon exiting
    the menu.

    Attributes:
        row_left (str): name of the item
        header (str): header message displayed above the scrolling, selectable items
        helptext (str): explanatory help message for this item
        chosen (bool): represents whether the user has chosen to run the configuration
    """

    def __init__(self,
                 row_left="Run",
                 header=None,
                 helptext=None,):
        super(RunItem, self).__init__(row_left=row_left, header=header, helptext=helptext)
        self.chosen = False

    def __call__(self):
        self.chosen = True

    def get_value(self):
        return self.chosen


class MenuItemError(Exception):
    """Base class for exceptions in this module."""
    pass


class MenuItemMissingValueError(MenuItemError):
    """Raised when the call to instantiation a class is missing an argument."""
    def __init__(self, arg_name):
        message = "Missing argument: {}".format(arg_name)
        super(MenuItemMissingValueError, self).__init__(message)
