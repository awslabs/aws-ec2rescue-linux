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
#
# Portions Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015 Python Software Foundation.
# All rights reserved.
# Please see LICENSE for applicable license terms and NOTICE for applicable notices.
# Details on all modifications are included within the comments.


"""
Simple textbox editing widget with Emacs-like keybindings.
This is the stock textpad class from Python 3.4.3 with the following changes:
1. rectangle()                       the draw calls inside a try/except block to prevent out of bounds exceptions
from crashing the program
2. Textbox._insert_printable_char()  fixed possible assignment before reference issue
3. Textbox.do_command()              added additional key bindings
4. Textbox.edit()                    made the cursor visible for the duration of this function
5. Textbox.__init__()                use background color pair 2
6. Docstring additions/improvements
"""
import sys

try:
    import curses
    import curses.ascii
except ImportError:  # pragma: no cover
    print("ERROR:\tMissing Python module 'curses'.")
    print("\tPlease install this module and rerun ec2rl")
    sys.exit(1)


def rectangle(win, uly, ulx, lry, lrx):
    """
    Draw a rectangle with corners at the provided upper-left and lower-right
    coordinates.

    Parameters:
        win (WindowObject): the screen/window
        uly (int): upper left y coordinate
        ulx (int): upper left x coordinate
        lry (int): lower right y coordinate
        lrx (int): lower right x coordinate

    Returns:
        None
    """
    # Add exception handling
    try:
        win.vline(uly + 1, ulx, curses.ACS_VLINE, lry - uly - 1)
        win.hline(uly, ulx + 1, curses.ACS_HLINE, lrx - ulx - 1)
        win.hline(lry, ulx + 1, curses.ACS_HLINE, lrx - ulx - 1)
        win.vline(uly + 1, lrx, curses.ACS_VLINE, lry - uly - 1)
        win.addch(uly, ulx, curses.ACS_ULCORNER)
        win.addch(uly, lrx, curses.ACS_URCORNER)
        win.addch(lry, lrx, curses.ACS_LRCORNER)
        win.addch(lry, ulx, curses.ACS_LLCORNER)
    # Catch attempts to print a character out of the bounds of the window
    except curses.error:
        pass


class Textbox(object):
    """
    Editing widget using the interior of a window object.
    Supports the following Emacs-like key bindings:

    Ctrl-A      Go to left edge of window.
    Ctrl-B      Cursor left, wrapping to previous line if appropriate.
    Ctrl-D      Delete character under cursor.
    Ctrl-E      Go to right edge (stripspaces off) or end of line (stripspaces on).
    Ctrl-F      Cursor right, wrapping to next line when appropriate.
    Ctrl-G      Terminate, returning the window contents.
    Ctrl-H      Delete character backward.
    Ctrl-J      Terminate if the window is 1 line, otherwise insert newline.
    Ctrl-K      If line is blank, delete it, otherwise clear to end of line.
    Ctrl-L      Refresh screen.
    Ctrl-N      Cursor down; move down one line.
    Ctrl-O      Insert a blank line at cursor location.
    Ctrl-P      Cursor up; move up one line.

    Move operations do nothing if the cursor is at an edge where the movement
    is not possible.  The following synonyms are supported where possible:

    KEY_LEFT = Ctrl-B, KEY_RIGHT = Ctrl-F, KEY_UP = Ctrl-P, KEY_DOWN = Ctrl-N
    KEY_BACKSPACE = Ctrl-h
    """
    def __init__(self, win, insert_mode=False, bkgd_color=None):
        self.win = win
        self.insert_mode = insert_mode
        (self.maxy, self.maxx) = win.getmaxyx()
        self.maxy -= 1
        self.maxx -= 1
        self.stripspaces = 1
        self.lastcmd = None
        win.keypad(1)
        if bkgd_color:
            win.bkgd(" ", bkgd_color)

    def _end_of_line(self, y):
        """Go to the location of the first blank on the given line,
        returning the index of the last non-blank character."""
        last = self.maxx
        while True:
            if curses.ascii.ascii(self.win.inch(y, last)) != curses.ascii.SP:
                last = min(self.maxx, last + 1)
                break
            elif last == 0:
                break
            last -= 1
        return last

    def _insert_printable_char(self, ch):
        (y, x) = self.win.getyx()
        if y < self.maxy or x < self.maxx:
            # Possible reference before assignment fix
            oldch = None
            if self.insert_mode:
                oldch = self.win.inch()
            # The try-catch ignores the error we trigger from some curses
            # versions by trying to write into the lowest-rightmost spot
            # in the window.
            try:
                self.win.addch(ch)
            except curses.error:
                pass
            if self.insert_mode:
                (backy, backx) = self.win.getyx()
                if curses.ascii.isprint(oldch):
                    self._insert_printable_char(oldch)
                    self.win.move(backy, backx)

    def do_command(self, ch):
        """Process a single editing command."""
        (y, x) = self.win.getyx()
        self.lastcmd = ch
        if curses.ascii.isprint(ch):
            if y < self.maxy or x < self.maxx:
                self._insert_printable_char(ch)
        elif ch == curses.ascii.SOH:                           # ^a # pragma: no coverage
            self.win.move(y, 0)
        # The backspace on a Lenovo T510 maps to ascii delete (127)
        # and the delete key maps to KEY_DC
        elif ch in (curses.ascii.DEL, curses.KEY_DC,
                    curses.ascii.STX, curses.KEY_LEFT,
                    curses.ascii.BS, curses.KEY_BACKSPACE):
            if x > 0:
                self.win.move(y, x - 1)
            elif y == 0:
                pass
            elif self.stripspaces:
                self.win.move(y - 1, self._end_of_line(y - 1))
            else:
                self.win.move(y - 1, self.maxx)
            # The backspace on a Lenovo T510 maps to ascii delete (127)
            # and the delete key maps to KEY_DC
            if ch in (curses.ascii.DEL, curses.KEY_DC,
                      curses.ascii.BS, curses.KEY_BACKSPACE):
                self.win.delch()
        elif ch == curses.ascii.EOT:                           # ^d
            self.win.delch()
        elif ch == curses.ascii.ENQ:                           # ^e  # pragma: no coverage
            if self.stripspaces:
                self.win.move(y, self._end_of_line(y))
            else:
                self.win.move(y, self.maxx)
        elif ch in (curses.ascii.ACK, curses.KEY_RIGHT):       # ^f
            if x < self.maxx:
                self.win.move(y, x + 1)
            elif y == self.maxy:
                pass
            else:
                self.win.move(y + 1, 0)
        elif ch == curses.ascii.BEL:                           # ^g
            return 0
        elif ch == curses.ascii.NL:                            # ^j
            if self.maxy == 0:
                return 0
            elif y < self.maxy:
                self.win.move(y + 1, 0)
        elif ch == curses.ascii.VT:                            # ^k # pragma: no coverage
            if x == 0 and self._end_of_line(y) == 0:
                self.win.deleteln()
            else:
                # first undo the effect of self._end_of_line
                self.win.move(y, x)
                self.win.clrtoeol()
        elif ch == curses.ascii.FF:                            # ^l # pragma: no coverage
            self.win.refresh()
        elif ch in (curses.ascii.SO, curses.KEY_DOWN):         # ^n
            if y < self.maxy:
                self.win.move(y + 1, x)
                if x > self._end_of_line(y + 1):
                    self.win.move(y + 1, self._end_of_line(y + 1))
        elif ch == curses.ascii.SI:                            # ^o # pragma: no coverage
            self.win.insertln()
        elif ch in (curses.ascii.DLE, curses.KEY_UP):          # ^p
            if y > 0:
                self.win.move(y - 1, x)
                if x > self._end_of_line(y - 1):
                    self.win.move(y - 1, self._end_of_line(y - 1))
        return 1

    def gather(self):
        """Collect and return the contents of the window."""
        result = ""
        for y in range(self.maxy + 1):
            self.win.move(y, 0)
            stop = self._end_of_line(y)
            if stop == 0 and self.stripspaces:
                continue
            for x in range(self.maxx + 1):
                if self.stripspaces and x > stop:
                    break
                result += chr(curses.ascii.ascii(self.win.inch(y, x)))
            if self.maxy > 0:
                result += "\n"
        return result

    def edit(self, validate=None):
        """Edit in the widget window and collect the results."""
        # Make the cursor visible and update the screen
        curses.curs_set(1)
        self.win.refresh()
        while 1:
            ch = self.win.getch()
            if validate:
                ch = validate(ch)
            if not ch:
                continue
            if not self.do_command(ch):
                break
            self.win.refresh()
        # Hide the cursor
        curses.curs_set(0)
        return self.gather()
