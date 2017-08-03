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

"""Unit tests for "menu_textpad_mod" module."""
import curses
import os
import sys
import unittest

import mock

import ec2rlcore.menu_textpad_mod


class TestMenuTextpadMod(unittest.TestCase):
    """Testing class for "menu_textpad_mod" unit tests."""

    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    if os.path.isdir(_callp):
        callpath = _callp
    else:
        callpath = os.path.split(_callp)[0]

    def setUp(self):
        """Default Options."""
        return

    def tearDown(self):
        """Clean up files and objects created during testing."""
        return

    def test_menu_textpad_mod_rectangle_exception(self):
        """Test that curses.error is not raised when drawing outside the bounds of the window."""
        def test_function(stdscr):
            stdscr.clear()
            stdscr = curses.initscr()
            ec2rlcore.menu_textpad_mod.rectangle(stdscr, curses.LINES + 1, curses.COLS + 1, 0, 0)

        curses.wrapper(test_function)
