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

"""Unit tests for "menu" module."""
import os
import sys
import unittest

if sys.hexversion >= 0x3030000:
    # shutil.get_terminal_size was introduced in Python 3.3
    from shutil import get_terminal_size
else:
    # backports.shutil_get_terminal_size is a backport of shutil's get_termiminal_size from Python 3.3
    from backports.shutil_get_terminal_size import get_terminal_size

import ec2rlcore.menu
import ec2rlcore.menu_item


class TestMenu(unittest.TestCase):
    """Testing class for "menu_backend" unit tests."""

    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    if os.path.isdir(_callp):
        callpath = _callp
    else:
        callpath = os.path.split(_callp)[0]

    def setUp(self):
        """Default Options."""
        self.menu = ec2rlcore.menu.Menu(row_left="root",
                                        header="Select an option:",
                                        helptext="This is the root menu and it has no help option.",
                                        footer_items=["Select", "Exit", "Help"])

    def test_menu_missing_row_left(self):
        """Test that instantiating a new Menu without the row_left value raises MenuMissingValueError."""
        with self.assertRaises(ec2rlcore.menu.MenuMissingValueError) as error:
            self.menu = ec2rlcore.menu.Menu(header="Select an option:",
                                            helptext="This is the root menu and it has no help option.",
                                            footer_items=["Select", "Exit", "Help"])
        self.assertEqual(str(error.exception), "Missing argument: row_left")

    def test_menu_missing_header(self):
        """Test that instantiating a new Menu without the header value raises MenuMissingValueError."""
        with self.assertRaises(ec2rlcore.menu.MenuMissingValueError) as error:
            self.menu = ec2rlcore.menu.Menu(row_left="root",
                                            helptext="This is the root menu and it has no help option.",
                                            footer_items=["Select", "Exit", "Help"])
        self.assertEqual(str(error.exception), "Missing argument: header")

    def test_menu_missing_helptext(self):
        """Test that instantiating a new Menu without the helptext value raises MenuMissingValueError."""
        with self.assertRaises(ec2rlcore.menu.MenuMissingValueError) as error:
            self.menu = ec2rlcore.menu.Menu(row_left="root",
                                            header="Select an option:",
                                            footer_items=["Select", "Exit", "Help"])
        self.assertEqual(str(error.exception), "Missing argument: helptext")

    def test_menu_missing_footer_items(self):
        """Test that instantiating a new Menu without the footer_items value raises MenuMissingValueError."""
        with self.assertRaises(ec2rlcore.menu.MenuMissingValueError) as error:
            self.menu = ec2rlcore.menu.Menu(row_left="root",
                                            header="Select an option:",
                                            helptext="This is the root menu and it has no help option.")
        self.assertEqual(str(error.exception), "Missing argument: footer_items")

    def test_menu_add(self):
        """Test that __add__ enables string concatenation and the result is as expected."""
        self.assertEqual(self.menu + "b", "    rootb")

    def test_menu_radd(self):
        """Test that __radd__ enables string concatenation and the result is as expected."""
        self.assertEqual("b" + self.menu, "b    root")

    def test_menu_item_format(self):
        """Test that __format__ enables use with the string formatter."""
        self.assertEqual("b {}".format(self.menu), "b root --->")
