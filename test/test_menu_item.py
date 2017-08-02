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

"""Unit tests for "menu_item" module."""
import curses
import curses.ascii
import os
import sys
import unittest

import ec2rlcore.menu_item


class TestMenuItem(unittest.TestCase):
    """Testing class for "menu_item" unit tests."""

    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    if os.path.isdir(_callp):
        callpath = _callp
    else:
        callpath = os.path.split(_callp)[0]

    def setUp(self):
        """Instantiate one of each type of menu object."""
        self.menuitem = ec2rlcore.menu_item.MenuItem(row_left="Test row_left",
                                                     header="Test header",
                                                     helptext="Test helptext")
        self.exititem = ec2rlcore.menu_item.ExitItem(row_left="Test row_left",
                                                     header="Test header",
                                                     helptext="Test helptext")
        self.toggleitem = ec2rlcore.menu_item.ToggleItem(row_left="Test row_left",
                                                         header="Test header",
                                                         helptext="Test helptext")
        self.textentryitem = ec2rlcore.menu_item.TextEntryItem(row_left="Test row_left",
                                                               header="Module '{}' - configure argument:".
                                                               format("Test module"),
                                                               helptext="Test help",
                                                               message="Test message")

    def test_menu_item_missing_row_left(self):
        """
        Test that instantiating a new Menu without the row_left value raises MenuMissingValueError and that the
        message includes the name of the missing value.
        """
        with self.assertRaises(ec2rlcore.menu_item.MenuItemMissingValueError) as error:
            self.textentryitem = ec2rlcore.menu_item.TextEntryItem(header="Test header:",
                                                                   helptext="Test helptext.")
        self.assertEqual(str(error.exception), "Missing argument: row_left")

    def test_menu_item_missing_header(self):
        """
        Test that instantiating a new Menu without the header value raises MenuMissingValueError and that the
        message includes the name of the missing value.
        """
        with self.assertRaises(ec2rlcore.menu_item.MenuItemMissingValueError) as error:
            self.textentryitem = ec2rlcore.menu_item.TextEntryItem(row_left="Test row_left",
                                                                   helptext="Test helptext.")
        self.assertEqual(str(error.exception), "Missing argument: header")

    def test_menu_item_missing_helptext(self):
        """
        Test that instantiating a new Menu without the helptext value raises MenuMissingValueError and that the
        message includes the name of the missing value.
        """
        with self.assertRaises(ec2rlcore.menu_item.MenuItemMissingValueError) as error:
            self.textentryitem = ec2rlcore.menu_item.TextEntryItem(row_left="Test row_left",
                                                                   header="Test header:")
        self.assertEqual(str(error.exception), "Missing argument: helptext")

    def test_menu_item_call_notimplemented(self):
        """
        Test that calling a MenuItem value raises NotImplementedError.
        This method is to be implemented in derived classes only.
        """
        with self.assertRaises(NotImplementedError) as error:
            self.menuitem()
        self.assertEqual(str(error.exception), "Method unimplemented in base MenuItem class.")

    def test_menu_item_get_value_notimplemented(self):
        """
        Test that calling Menuitem.get_value() raises NotImplementedError.
        This method is to be implemented in derived classes only.
        """
        with self.assertRaises(NotImplementedError) as error:
            self.menuitem.get_value()
        self.assertEqual(str(error.exception), "Method unimplemented in base MenuItem class.")

    def test_menu_item_add(self):
        """
        Test that __add__ enables string concatenation and the result is as expected.
        These tests concatenation where the TextEntryItem is the LHS of the "+" operator.
        """
        self.assertEqual(self.textentryitem + "b", "    Test row_leftb")

    def test_menu_item_radd(self):
        """
        Test that __radd__ enables string concatenation and the result is as expected.
        These tests concatenation where the TextEntryItem is the RHS of the "+" operator.
        """
        self.assertEqual("b" + self.textentryitem, "b    Test row_left")

    def test_menu_item_format(self):
        """Test that __format__ enables use with the string formatter."""
        self.textentryitem.row_right = "a"
        self.assertEqual("b '{}'".format(self.textentryitem), "b 'Test row_left a'")

    def test_menu_item_textentryitem(self):
        """Test that TextEntryItem obtains user input when called and that get_value() returns the stored value."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch("a")
        self.textentryitem()
        self.assertEqual(self.textentryitem.get_value(), "a")

    def test_menu_item_toggleitem_default_value(self):
        """Test that ToggleItem is toggled by default."""
        self.assertTrue(self.toggleitem.toggled)

    def test_menu_item_toggleitem_call(self):
        """Test that calling ToggleItem toggles it off and on."""
        self.assertTrue(self.toggleitem.toggled)
        self.toggleitem()
        self.assertFalse(self.toggleitem.toggled)
        self.toggleitem()
        self.assertTrue(self.toggleitem.toggled)

    def test_menu_item_exititem_get_value(self):
        """Test that ExitItem.get_value returns None."""
        self.assertEqual(self.exititem.get_value(), None)

    def test_menu_textentryitem__eot_deletion(self):
        """Test that the input_caller returns the expected string value."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch("a")
        curses.ungetch(curses.ascii.EOT)
        curses.ungetch(curses.ascii.EOT)
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch(curses.ascii.EOT)
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch("a")
        curses.ungetch("a")
        self.textentryitem()
        self.assertEqual(self.textentryitem.get_value(), "a")

    def test_menu_textentryitem__deletion(self):
        """Test that the input_caller returns the expected string value."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch("a")
        curses.ungetch(curses.KEY_BACKSPACE)
        curses.ungetch(curses.KEY_BACKSPACE)
        curses.ungetch(curses.KEY_BACKSPACE)
        curses.ungetch("a")
        curses.ungetch("a")
        self.textentryitem()
        self.assertEqual(self.textentryitem.get_value(), "a")

    def test_menu_textentryitem__overwrite_insert(self):
        """Test that the input_caller returns the expected string value."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_IC)
        curses.ungetch("b")
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch("a")
        curses.ungetch(curses.KEY_IC)
        self.textentryitem()
        self.assertEqual(self.textentryitem.get_value(), "b")

    def test_menu_textentryitem__key_right(self):
        """Test that the input_caller returns the expected string value."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch("b")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("a")
        self.textentryitem()
        self.assertEqual(self.textentryitem.get_value(), "a b")

    def test_menu_textentryitem__ascii_bel(self):
        """Test that the input_caller returns the expected string value."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.ascii.BEL)
        # BEL is a non-printable character so the return value should be an empty string
        self.textentryitem()
        self.assertEqual(self.textentryitem.get_value(), "")

    def test_menu_textentryitem__key_up(self):
        """Test that the input_caller returns the expected string value."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_UP)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch("a")
        self.textentryitem()
        self.assertEqual(self.textentryitem.get_value(), "a")
