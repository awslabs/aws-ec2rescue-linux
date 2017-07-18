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
This module contains the object class for a menu.

Functions:
    None

Classes:
    Menu: representation of a menu of choosable items which could be other Menu objects or MenuItem-derived objects.

Exceptions:
    MenuError: base error class for this module.
    MenuUnsupportedFooterOptionError: raised when an unsupported footer action is encountered.
    MenuMissingValueError: raised when the call to instantiation a class is missing an argument.
"""
from __future__ import division
import curses
import math
import os

import ec2rlcore.menu_item


class Menu(object):
    """
    Representation of a menu with items the user can select.
    The items can be submenus of type Menu or items of type MenuItem.

    Attributes:
        row_left (str): right half of the row item; typically the name of the menu
        header (str): message displayed above the selectable items in the list attribute
        helptext (str): a longer explanatory help message for this menu
        _items (list): list of items that are selectable by the user on the Y axis
        _items_dict (dict): dict mapping of items in _dict using MenuItem.row_left as the key
        footer_items (list): list of footer items that are selectable by the user on the X axis
        current_row (int): the currently selected window row
        current_column (int): the list index of the currently selected item in the footer
        current_page (int): the current page of MenuItems being viewed
        done (bool): tracks whether the menu should return or continue obtaining character input from the user
        toggle_state (bool): tracks which state the toggle all key bind should perform (select/deselect all)
    """
    def __init__(self,
                 row_left=None,
                 header=None,
                 helptext=None,
                 footer_items=None):
        if not row_left:
            raise MenuMissingValueError("row_left")
        if not header:
            raise MenuMissingValueError("header")
        if not helptext:
            raise MenuMissingValueError("helptext")
        if not footer_items:
            raise MenuMissingValueError("footer_items")

        self.row_left = row_left
        self.header = header
        self.helptext = "{}\n\n{}".format(row_left.strip(), helptext)
        self._items = []
        self._items_dict = {}
        self.footer_items = footer_items
        self.current_row = 1
        self.current_column = 0
        self.current_page = 1
        self.done = False
        self.toggle_state = True
        self.key_bind_help = ["Arrow keys navigate the menu.",
                              "<enter> selects submenus.",
                              "<space> selects/deselects items.",
                              "N selects/deselects all items.",
                              "Legend: ---> submenu.",
                              "---- empty submenu.",
                              "[*] selected.",
                              "[ ] unselected."]

    @property
    def row_right(self):
        if len(self._items) == 1 and isinstance(self._items[0], ec2rlcore.menu_item.ExitItem):
            return "----"
        else:
            return "--->"

    @property
    def num_rows(self):
        return len(self._items)

    @property
    def max_displayed_rows(self):
        # Return how many items can be displayed in the primary subwindow for displaying the dict items
        return curses.LINES - 9

    @property
    def num_pages(self):
        # Define how many pages of items exist
        # division imported from __future__ for consistent behavior
        # See PEP 238: https://www.python.org/dev/peps/pep-0238/
        return int(math.ceil(self.num_rows / self.max_displayed_rows))

    @property
    def num_columns(self):
        return len(self.footer_items)

    # Support for builtin len()
    def __len__(self):
        return len(self._items)

    # Support for printing the object as a string
    def __str__(self):
        return "    " + self.row_left

    # Support for printing with str.format()
    def __format__(self, *args, **kwargs):
        return " ".join((self.row_left, self.row_right))

    # Support for concatenation operator '+'
    def __add__(self, other):
        return str(self) + other

    # Support for concatenation operator '+'
    def __radd__(self, other):
        return other + str(self)

    # Support for indexed access
    def __getitem__(self, index):
        if isinstance(index, int):
            return self._items[index]
        elif isinstance(index, str):
            return self._items_dict[index]
        else:
            return None

    def append(self, new_item):
        if isinstance(new_item, (Menu, ec2rlcore.menu_item.MenuItem)):
            self._items.append(new_item)
            self._items_dict[new_item.row_left] = new_item
        return self._items

    def get_items(self):
        return self._items

    def get_items_dict_copy(self):
        # Returns a copy of _items_dict whose values are all strings (for ConfigParser safety)
        items_dict = {}
        for key in self._items_dict:
            items_dict[key] = str(self._items_dict[key].get_value())
        return items_dict

    def get_item_keys(self):
        return self._items_dict.keys()

    def get_value(self):
        return self.row_left

    def remove(self, item):
        if isinstance(item, (Menu, ec2rlcore.menu_item.MenuItem)):
            try:
                self._items.remove(item)
                del self._items_dict[item.row_left]
            except ValueError:
                pass
        return self._items

    def __call__(self):
        while True:
            curses.wrapper(self.setup)
            if self.done:
                return True

    def _draw_menu(self, screen):
        """
        Given a menu window, draw the rows including the header and the scrollable rows representing menu items.

        Parameters:
            screen (WindowObject): the window that will be drawn to
        """
        # Add the header
        screen.addstr(0, int((curses.COLS - 6) / 2 - len(self.header) / 2),
                      self.header,
                      curses.A_BOLD)

        # Add each item to the menu
        for row in range(1 + (self.max_displayed_rows * (self.current_page - 1)),
                         self.max_displayed_rows + 1 +
                         (self.max_displayed_rows * (self.current_page - 1))):
            # Pad or truncate the module name to 40 characters
            row_item_name = "{:40}".format(str(self._items[row - 1])[:40])
            # Truncate the row's string to the drawable width
            display_str = str(row_item_name + "  " + self._items[row - 1].row_right)[:curses.COLS - 6]
            # Draw the row
            if row + (self.max_displayed_rows * (self.current_page - 1)) == \
                self.current_row + \
                    (self.max_displayed_rows * (self.current_page - 1)):
                # Highlight the item that is currently selected
                screen.addstr(row - (self.max_displayed_rows * (self.current_page - 1)),
                              1,
                              display_str.rstrip(),
                              curses.color_pair(1) | curses.A_BOLD)
            else:
                screen.addstr(row - (self.max_displayed_rows * (self.current_page - 1)),
                              1,
                              display_str)

            # Stop printing items when the end of the drawable space is reached
            if row == self.num_rows:
                break

    def _draw_footer(self, footer_window):
        """
        Given a footer window and a list of items, draw the items in the footer and highlight the selected item.

        Parameters:
            footer_window (WindowObject): the window the footer will be drawn in
        """
        for item in self.footer_items:
            if self.footer_items.index(item) == self.current_column:
                # Highlight the item that is currently selected
                footer_window.addstr(1,
                                     self.footer_items.index(item) * 10 + 1,
                                     item,
                                     curses.color_pair(1) | curses.A_BOLD)
            else:
                footer_window.addstr(1,
                                     self.footer_items.index(item) * 10 + 1,
                                     item)

    def draw_menu(self, stdscr):
        # Setup the title
        # bitwise OR the color_pair and A_BOLD ints since addstr can only take one attr int
        stdscr.addstr(0, 0, "ec2rl module configurator", curses.color_pair(2) | curses.A_BOLD)
        stdscr.chgat(-1, curses.color_pair(2))
        curses.curs_set(0)

        # Configure a main window to hold the subwindows
        main_window = curses.newwin(curses.LINES - 1, curses.COLS, 1, 0)

        tmp_str = ""
        x_pos = 0
        for item in self.key_bind_help:
            if len(tmp_str) + len(item) < curses.COLS - 6:
                if not tmp_str:
                    tmp_str += item
                else:
                    tmp_str = "  ".join((tmp_str, item))
            else:
                main_window.addstr(x_pos, 3, tmp_str)
                tmp_str = ""
                tmp_str += item
                x_pos += 1
        main_window.addstr(x_pos, 3, tmp_str)

        # Create subwindows for displaying dict items and a footer for select/exit
        screen = main_window.subwin(curses.LINES - 7, curses.COLS - 4, 4, 2)
        footer = main_window.subwin(3, curses.COLS - 4, curses.LINES - 3, 2)

        # Setup background colors
        main_window.bkgd(" ", curses.color_pair(1))
        screen.bkgd(" ", curses.color_pair(2))
        footer.bkgd(" ", curses.color_pair(2))

        # Draw borders around the subwindows
        screen.box()
        footer.box()

        # Erase the screen so it can be cleanly redrawn
        screen.erase()
        screen.border(0)

        # Draw the initial screen for the user prior to entering the user input handling loop
        self._draw_menu(screen)
        # Add the footer
        self._draw_footer(footer)

        # Update the pieces
        stdscr.noutrefresh()
        main_window.noutrefresh()
        screen.noutrefresh()
        footer.noutrefresh()
        curses.doupdate()

        return main_window, screen, footer

    def setup(self, stdscr):
        """
        Draw the menu and handle keyboard input.

        Parameters:
            stdscr (WindowObject): the screen; handled by curses.wrapper

        Returns:
            the string representing the currently selected row
        """

        # Initialize the WindowObject
        stdscr.clear()
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()

        # Start color support if supported
        if curses.has_colors():
            curses.start_color()

        # Initialize color pairs
        # Main window
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        # Sub-windows
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)

        # Verify this is a terminal that is at least both 80 columns and 24 lines
        if curses.LINES < 24 or curses.COLS < 80:
            raise curses.error(
                "Required minimum terminal dimensions of 80x24 > {}x{}.".format(curses.COLS, curses.LINES))

        main_window, screen, footer = self.draw_menu(stdscr)

        # Menu loop until item is chosen with the <enter> key or the user quits with "q"
        while True:
            # Get a character from the keyboard
            key = stdscr.getch()
            # Enter selects the highlighted item
            if key == ord("\n"):
                footer_selection = self.footer_items[self.current_column]
                if footer_selection == "Select":
                    if isinstance(self._items[self.current_row - 1], (ec2rlcore.menu_item.ExitItem,
                                                                      ec2rlcore.menu_item.RunItem)):
                        self._items[self.current_row - 1]()
                        self.current_row = 1
                        self.current_column = 0
                        self.current_page = 1
                        self.done = True
                        return
                    else:
                        self.current_column = 0
                        return self._items[self.current_row - 1]()
                elif footer_selection == "Exit":
                    self.current_row = 1
                    self.current_column = 0
                    self.current_page = 1
                    self.done = True
                    return
                elif footer_selection == "Help":
                    self.current_column = 0
                    return self.show_item_help(self._items[self.current_row - 1])
                elif footer_selection == "Clear":
                    if isinstance(self._items[self.current_row - 1], ec2rlcore.menu_item.TextEntryItem):
                        self._items[self.current_row - 1].row_right = ""
                else:
                    raise MenuUnsupportedFooterOptionError(footer_selection)
            elif key == ord(" "):
                if isinstance(self._items[self.current_row - 1], ec2rlcore.menu_item.ToggleItem):
                    self._items[self.current_row - 1]()
            elif key in (78, "N"):
                # Select/deselect all ToggleItems in current menu
                for item in self._items:
                    if isinstance(item, ec2rlcore.menu_item.ToggleItem) \
                            and ((self.toggle_state and item.toggled) or (not self.toggle_state and not item.toggled)):
                        item()
                self.toggle_state = not self.toggle_state
            elif key in (260, curses.KEY_LEFT):
                if self.current_column > 0:
                    self.current_column -= 1
            # The right arrow key selects the footer option to the right of the currently selected item
            elif key in (261, curses.KEY_RIGHT):
                if self.current_column < self.num_columns - 1:
                    self.current_column += 1
            # The down arrow key selects the next option in the menu window and increments the page as needed
            elif key in (65, 258, curses.KEY_DOWN):
                if self.current_page == 1:
                    if self.current_row < self.max_displayed_rows and \
                                            self.current_row < self.num_rows:
                        self.current_row += 1
                    # Else + if num_pages > 1
                    elif self.num_pages > 1:
                        self.current_page += 1
                        self.current_row = 1 + (self.max_displayed_rows * (self.current_page - 1))
                elif self.current_page == self.num_pages:
                    if self.current_row < self.num_rows:
                        self.current_row += 1
                else:
                    if self.current_row < self.max_displayed_rows + \
                            (self.max_displayed_rows * (self.current_page - 1)):
                        self.current_row += 1
                    else:
                        self.current_page += 1
                        self.current_row = 1 + (self.max_displayed_rows * (self.current_page - 1))
            # The up arrow key selects the previous option in the menu window and decrements the page as needed
            elif key in (66, 259, curses.KEY_UP):
                if self.current_page == 1:
                    if self.current_row > 1:
                        self.current_row -= 1
                else:
                    if self.current_row > (1 + (self.max_displayed_rows * (self.current_page - 1))):
                        self.current_row -= 1
                    else:
                        self.current_page -= 1
                        self.current_row = \
                            self.max_displayed_rows + (self.max_displayed_rows * (self.current_page - 1))
            # The page down key increments the page  and selects the row in the same position in the menu on that page
            # or the first row if the next page doesn't have an equivalent row
            # Ignore page down key presses on the last page
            elif key in (338, curses.KEY_NPAGE) and self.current_page < self.num_pages:
                self.current_page += 1
                # Bounds check to ensure there are enough items on the next page to select an item in the same position
                # This will be true for all pages but the last page which will likely be a partial page of items
                if self.current_row + self.max_displayed_rows < self.num_rows:
                    self.current_row += self.max_displayed_rows
                # If the bounds check fails then select the first item on the next (last) page
                else:
                    self.current_row = ((self.current_page - 1) * self.max_displayed_rows) + 1
            # The page up key decrements the page and selects the row in the same position in the menu on that page
            # Ignore page up key presses when on the first page
            elif key in (339, curses.KEY_PPAGE) and self.current_page > 1:
                self.current_page -= 1
                # Shift the currently selected row to the same place on the new page
                self.current_row -= self.max_displayed_rows
            elif key in (410, curses.KEY_RESIZE):
                # Get the new terminal dimensions and resize the terminal
                curses.resizeterm(*stdscr.getmaxyx())

                # Verify the terminal is still at least 80x24
                if curses.LINES < 24 or curses.COLS < 80:
                    raise curses.error(
                        "Required minimum terminal dimensions of 80x24 > {}x{}.".format(curses.COLS, curses.LINES))

                # Initialize a new WindowObject
                stdscr = curses.initscr()
                curses.noecho()
                curses.cbreak()

                main_window, screen, footer = self.draw_menu(stdscr)

                # Recalculate the current page
                # current_selected_row - 1 is needed because the row in the window is offset by 1
                self.current_page = int(math.ceil(self.current_row / self.max_displayed_rows))

                # For some reason, another getch() call is required to pull the KEY_RESIZE out of the buffer
                stdscr.getch()

            # Erase the screen so it can be cleanly redrawn
            screen.erase()
            screen.border(0)

            self._draw_menu(screen)

            # Draw the navigation items in the footer
            self._draw_footer(footer)

            # Draw the pieces of the overall screen (order matters)
            stdscr.noutrefresh()
            main_window.noutrefresh()
            screen.noutrefresh()
            footer.noutrefresh()
            curses.doupdate()

    def show_item_help(self, menu_item):
        return curses.wrapper(self._draw_notification, menu_item.helptext)

    @staticmethod
    def _draw_notification(stdscr, message):
        """
        Draw a notification window with the provided message.

        Parameters:
            stdscr (WindowObject): the screen; handled by curses.wrapper
            message (str): the message to the user

        Returns:
            True (bool)
        """
        stdscr.clear()

        # Setup the title
        stdscr.addstr("ec2rl module configurator", curses.color_pair(2) | curses.A_BOLD)
        stdscr.chgat(-1, curses.color_pair(2))
        curses.curs_set(0)

        message_list = [message.rstrip() for message in message.split(os.linesep)]
        current_row = 1

        main_window = curses.newwin(curses.LINES - 1, curses.COLS, 1, 0)
        screen = main_window.subwin(curses.LINES - 7, curses.COLS - 4, 4, 2)
        footer = main_window.subwin(3, curses.COLS - 4, curses.LINES - 3, 2)

        # Setup background colors
        main_window.bkgd(" ", curses.color_pair(1))
        screen.bkgd(" ", curses.color_pair(2))
        footer.bkgd(" ", curses.color_pair(2))

        # Draw borders around the subwindows
        screen.box()
        footer.box()

        footer.addstr(1, 1, "Exit", curses.color_pair(1) | curses.A_BOLD)

        for message in message_list:
            if current_row < curses.LINES - 7:
                # Truncate the string, if needed
                display_str = message[:curses.COLS - 8]
                screen.addstr(current_row, 3, display_str)
                current_row += 1
            else:
                break

        # Draw the pieces of the overall screen (order matters)
        stdscr.noutrefresh()
        main_window.noutrefresh()
        screen.noutrefresh()
        curses.doupdate()

        while True:
            # Get a character from the keyboard
            key = stdscr.getch()
            # The user can exit via the enter key
            if key == ord("\n"):
                return True


class MenuError(Exception):
    """Base class for exceptions in this module."""
    pass


class MenuUnsupportedFooterOptionError(MenuError):
    """Raised when an unsupported footer action is encountered."""
    def __init__(self, option_name):
        message = "Encountered unsupported footer selection: {}".format(option_name)
        super(MenuUnsupportedFooterOptionError, self).__init__(message)


class MenuMissingValueError(MenuError):
    """Raised when the call to instantiation a class is missing an argument."""
    def __init__(self, arg_name):
        message = "Missing argument: {}".format(arg_name)
        super(MenuMissingValueError, self).__init__(message)
