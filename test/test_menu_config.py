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
Unit tests for "menu_config" module. Primarily uses curses.ungetch to simulate keyboard input.
Note that the input buffer acts like a stack so when reading the tests, keep in mind that the characters
are in reverse order.
"""
import curses
import mock
import os
import sys
import unittest

import ec2rlcore.menu
import ec2rlcore.menu_config
import ec2rlcore.menu_item
import ec2rlcore.module
import ec2rlcore.moduledir


class TestMenuConfig(unittest.TestCase):
    """Testing class for "menu_config" unit tests."""

    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    if os.path.isdir(_callp):
        callpath = _callp
    else:
        callpath = os.path.split(_callp)[0]

    module_path = os.path.join(callpath, "test/modules/mod.d")
    modules = ec2rlcore.moduledir.ModuleDir(module_path)

    def setUp(self):
        """Setup the module_config for use in the tests."""
        self.menu = ec2rlcore.menu_config.get_menu_config(self.modules)

    # @unittest.skip
    # # TODO there is no equivalent function in the new menu at this time
    # def test_menu_config_get_arg_dict_from_module(self):
    #     """Test that get_arg_dict_from_module returns an OrderedDict containing the expected keys."""
    #     module_obj = ec2rlcore.module.get_module(os.path.join(self.module_path, "atop.yaml"))
    #     arg_dict = ec2rlcore.menu_config.get_arg_dict_from_module(module_obj)
    #     self.assertIsInstance(arg_dict, collections.OrderedDict)
    #     self.assertEqual(arg_dict["period"], "")
    #     self.assertEqual(arg_dict["times"], "")

    def test_menu_config_top_level_selection(self):
        """Test that top_level_selection returns an OrderedDict containing the expected keys and values."""
        self.assertIsInstance(self.menu, ec2rlcore.menu.Menu)
        # Verify all the top level dicts are present
        self.assertIsInstance(self.menu["Configure global module arguments"], ec2rlcore.menu.Menu)
        self.assertIsInstance(self.menu["View all modules"], ec2rlcore.menu.Menu)
        self.assertIsInstance(self.menu["View modules, filtered by class"], ec2rlcore.menu.Menu)
        self.assertIsInstance(self.menu["View modules, filtered by domain"], ec2rlcore.menu.Menu)
        self.assertIsInstance(self.menu["Save and exit"], ec2rlcore.menu_item.ExitItem)
        self.assertIsInstance(self.menu["Run this configuration"], ec2rlcore.menu_item.RunItem)

        menu_all_modules = self.menu["View all modules"]
        menu_modules_by_class = self.menu["View modules, filtered by class"]
        menu_modules_by_domain = self.menu["View modules, filtered by domain"]

        # Verify all several modules are present in the "Modules" dict
        self.assertIsInstance(menu_all_modules["arpcache"], ec2rlcore.menu.Menu)
        self.assertIsInstance(menu_all_modules["arptable"], ec2rlcore.menu.Menu)
        self.assertIsInstance(menu_all_modules["arptablesrules"], ec2rlcore.menu.Menu)
        self.assertIsInstance(menu_all_modules["asymmetricroute"], ec2rlcore.menu.Menu)
        self.assertIsInstance(menu_all_modules["atop"], ec2rlcore.menu.Menu)
        self.assertIsInstance(menu_all_modules["nping"], ec2rlcore.menu.Menu)

        # Verify several the modules in the "Modules, by class" dict are references to the same modules in the "Modules"
        # dict. Also verifies modules were put in the correct class dict.
        self.assertEqual(menu_all_modules["arptable"],
                         menu_modules_by_class["View the 'collect' class of modules"]["arptable"])
        self.assertEqual(menu_all_modules["arptablesrules"],
                         menu_modules_by_class["View the 'collect' class of modules"]["arptablesrules"])
        self.assertEqual(menu_all_modules["atop"],
                         menu_modules_by_class["View the 'collect' class of modules"]["atop"])
        self.assertEqual(menu_all_modules["nping"],
                         menu_modules_by_class["View the 'collect' class of modules"]["nping"])
        self.assertEqual(menu_all_modules["arpcache"],
                         menu_modules_by_class["View the 'diagnose' class of modules"]["arpcache"])
        self.assertEqual(menu_all_modules["asymmetricroute"],
                         menu_modules_by_class["View the 'diagnose' class of modules"]["asymmetricroute"])

        # Verify several the modules in the "Modules, by domain" dict are references to the same modules in
        # the "Modules" dict. Also verifies modules were put in the correct domain dict.
        self.assertEqual(menu_all_modules["arpcache"],
                         menu_modules_by_domain["View the 'net' domain of modules"]["arpcache"])
        self.assertEqual(menu_all_modules["arptable"],
                         menu_modules_by_domain["View the 'net' domain of modules"]["arptable"])
        self.assertEqual(menu_all_modules["arptablesrules"],
                         menu_modules_by_domain["View the 'net' domain of modules"]["arptablesrules"])
        self.assertEqual(menu_all_modules["asymmetricroute"],
                         menu_modules_by_domain["View the 'net' domain of modules"]["asymmetricroute"])
        self.assertEqual(menu_all_modules["nping"],
                         menu_modules_by_domain["View the 'net' domain of modules"]["nping"])
        self.assertEqual(menu_all_modules["atop"],
                         menu_modules_by_domain["View the 'performance' domain of modules"]["atop"])

        # Verify the module dict key/value pairs are set correctly.
        self.assertEqual(menu_all_modules["atop"].helptext,
                         "atop\n\n"
                         "Collect output from atop for system analysis\n"
                         "Requires --times= for number of times to repeat\n"
                         "Requires --period= for length of sample period\n"
                         "Requires atop tool ( http://www.atoptool.nl/ )\n"
                         "Requires sudo: False")
        self.assertEqual(menu_all_modules["atop"].header,
                         "Module 'atop' - Select an option to configure:")
        self.assertEqual(menu_all_modules["atop"].row_left,
                         "atop")
        self.assertEqual(menu_all_modules["atop"].row_right,
                         "--->")
        self.assertEqual(menu_all_modules["atop"]["period"].get_value(),
                         "")
        self.assertEqual(menu_all_modules["atop"]["times"].get_value(),
                         "")

    def test_menu_config_global_arg_selection(self):
        """Test setting the Global arg 'only-domains' to 'performance'"""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(" ")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(" ")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(" ")
        # This key sequence may need to change if the Global args in the menu are modified.
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch("\n")
        self.menu()
        self.assertFalse(self.menu["Configure global module arguments"]["only-domains"]["application"].toggled)
        self.assertFalse(self.menu["Configure global module arguments"]["only-domains"]["net"].toggled)
        self.assertFalse(self.menu["Configure global module arguments"]["only-domains"]["os"].toggled)
        self.assertTrue(self.menu["Configure global module arguments"]["only-domains"]["performance"].toggled)

    def test_menu_config_global_arg_clear(self):
        """Test setting that the "Clear" footer option sets the Concurrency value to an empty string."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        # This key sequence may need to change if the Global args in the menu are modified.
        curses.ungetch("\n")
        curses.ungetch("1")
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch("\n")
        self.menu()
        self.assertEqual(self.menu["Configure global module arguments"]["concurrency"].get_value(), "")

    def test_menu_config_global_arg_clear_int_index(self):
        """
        Test setting that the "Clear" footer option sets the Concurrency value to an empty string.
        Verify using an integer index (e.g. list access).
        """
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        # This key sequence may need to change if the Global args in the menu are modified.
        curses.ungetch("\n")
        curses.ungetch("1")
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch("\n")
        self.menu()
        self.assertEqual(self.menu["Configure global module arguments"][3].get_value(), "")

    def test_menu_config_select_modules_no_module_args(self):
        """Test drawing the menus when selecting a module that contains no configuration args."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch("\n")
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())

    def test_menu_config_menu_scrolling_up(self):
        """Test paging down to the bottom of the Modules sub-menu thens scrolling up to the top."""
        curses.initscr()
        # Exit the menu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)

        # Test scrolling up to the top
        for i in range(len(self.modules)):
            curses.ungetch(curses.KEY_UP)

        # Go to the bottom of the Modules sub-menu
        for iteration in range(15):
            curses.ungetch(curses.KEY_NPAGE)

        # Get into the Modules submenu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())

    def test_menu_config_menu_scrolling_down(self):
        """Test scrolling down through the Modules sub-menu."""
        curses.initscr()
        # Exit the menu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)

        # Test scrolling down, line by line
        for i in range(len(self.modules)):
            curses.ungetch(curses.KEY_DOWN)

        # Get into the Modules submenu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())

    def test_menu_config_menu_scrolling_down_single_page(self):
        """Test scrolling down through the Global sub-menu."""
        curses.initscr()
        # Exit the menu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)

        # Test scrolling down, line by line, and one past the bottom
        for i in range(len(self.menu["Configure global module arguments"])):
            curses.ungetch(curses.KEY_DOWN)

        # Get into the Global submenu
        curses.ungetch("\n")
        self.assertTrue(self.menu())

    def test_menu_config_menu_pagination(self):
        """Test page up and page down key functionality."""
        curses.initscr()
        # Exit the menu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)

        # Test going up a page
        curses.ungetch(curses.KEY_PPAGE)

        # Test bounds checking on the last page
        curses.ungetch(curses.KEY_NPAGE)
        curses.ungetch(curses.KEY_UP)

        # Scroll all the way to the last page and attempt to go beyond
        for iteration in range(15):
            curses.ungetch(curses.KEY_NPAGE)

        # Get into the Modules submenu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())

    def test_menu_config_select_module_exit_selection(self):
        """Test drawing and exiting the menu."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch(curses.KEY_UP)
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())

    @mock.patch("curses.has_colors", side_effect=[False])
    def test_menu_config_select_module_exit_selection_no_colors(self, mock_side_effect_function):
        """Test drawing and exiting the menu when the terminal doesn't support colors."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        self.assertTrue(self.menu())
        self.assertTrue(mock_side_effect_function.called)

    def test_menu_config_key_resize(self):
        """Test redrawing the window in response to a resize keypress."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RESIZE)
        curses.ungetch(curses.KEY_RIGHT)
        self.assertTrue(self.menu())

    def test_menu_config_key_right_gt_footer_len(self):
        """Test behavior when attempting to select an item to the right of the rightmost footer items."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        self.assertTrue(self.menu())

    def test_menu_config_space_non_toggleitem(self):
        """Test behavior when attempting toggle a non-ToggleItem with the spacebar."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(" ")
        self.assertTrue(self.menu())

    def test_menu_config_toggle_all_on(self):
        """Test that "N" deselects then selects all items in the only-classes menu."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        # Selects all items
        curses.ungetch("N")
        # Deselects the remainder of the items
        curses.ungetch("N")
        # Deselect the first two items
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(" ")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(" ")
        curses.ungetch("\n")
        curses.ungetch("\n")
        self.assertTrue(self.menu())
        for item in self.menu["Configure global module arguments"]["only-classes"]:
            self.assertTrue(item.toggled)

    def test_menu_config_toggle_all_off(self):
        """Test that "N" deselects all items in the only-classes menu."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        # Deselect all items
        curses.ungetch("N")
        curses.ungetch("\n")
        curses.ungetch("\n")
        self.assertTrue(self.menu())
        for item in self.menu["Configure global module arguments"]["only-classes"]:
            self.assertFalse(item.toggled)

    def test_menu_config_toggle_all_on_mixed_items(self):
        """Test that "N" deselects then selects "perfimpact" in the Global args menu."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        # Select all items (turns perfimpact on)
        curses.ungetch("N")
        # Deselect all items (perfimpact is already off)
        curses.ungetch("N")
        # Toggle perfimpact off
        curses.ungetch(" ")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch("\n")
        self.assertTrue(self.menu())
        self.assertTrue(self.menu["Configure global module arguments"]["perfimpact"].toggled)

    def test_menu_config_toggle_all_off_mixed_items(self):
        """Test that "N" deselects "perfimpact" in the Global args menu."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        # Deselect all items
        curses.ungetch("N")
        curses.ungetch("\n")
        self.assertTrue(self.menu())
        self.assertFalse(self.menu["Configure global module arguments"]["perfimpact"].toggled)

    def test_menu_config_clear_non_textentryitem(self):
        """Test behavior when attempting clear a non-TextEntryItem."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        self.assertTrue(self.menu())

    def test_menu_config_view_module_help(self):
        """
        Test drawing the menu, selecting the modules menu, a module, and the module help, and then exiting the menu.
        """
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        # _draw_notifications only reacts to ord("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())

    def test_menu_config_view_empty_module_help(self):
        """
        Test drawing the menu, selecting the modules menu, a module, and the module help, and then exiting the menu.
        In this test the module help is an empty string.
        """
        self.menu["View all modules"]["aptlog"].helptext = ""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())

    def test_menu_config_view_long_module_help(self):
        """
        Test drawing the menu, selecting the modules menu, a module, and the module help, and then exiting the menu.
        In this test the help string is more (separated) lines than the window and should be truncated by the
        _draw_notification method.
        """
        # TODO working here
        num_messages = 0
        while num_messages < 100:
            self.menu["View all modules"]["aptlog"].helptext += "a\n"
            num_messages += 1
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())

    def test_menu_config_set_module_value(self):
        """Test drawing module option menu, configuring the period module option, and then exiting the menu."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch("1")
        curses.ungetch("\n")
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())
        self.assertEqual(self.menu["View all modules"]["atop"]["period"].get_value(),
                         "1")

    def test_menu_config_set_and_clear_module_value(self):
        """Test drawing module option menu, not configuring the period module option, and then exiting the menu."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch(curses.KEY_LEFT)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch(curses.KEY_RIGHT)
        curses.ungetch("\n")
        curses.ungetch("1")
        curses.ungetch("\n")
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        self.assertTrue(self.menu())
        self.assertEqual(self.menu["View all modules"]["atop"]["period"].get_value(),
                         "")

    def test_menu_unsupportedfooteroption(self):
        """Test that unsupported footer strings raise MenuUnsupportedFooterOptionError when encountered."""
        self.menu.footer_items = ["a"]
        curses.ungetch("\n")
        with self.assertRaises(ec2rlcore.menu.MenuUnsupportedFooterOptionError) as error:
            self.assertTrue(self.menu())
        self.assertEqual(str(error.exception), "Encountered unsupported footer selection: a")

    def test_menu_indexed_access_other_type(self):
        """Test that accessing an item via a non-string, non-int, returns None."""
        self.assertEqual(self.menu[{}], None)

    def test_menu_remove_nonexistent_non_menuitem(self):
        """Test that removing a non-MenuItem does not modify the object's contents."""
        original_length = len(self.menu)
        self.menu.remove("asdf")
        self.assertEqual(original_length, len(self.menu))
        self.assertEqual(self.menu.get_items_dict_copy(),
                         {"Save and exit": "None",
                          "Configure global module arguments": "Configure global module arguments",
                          "View modules, filtered by class": "View modules, filtered by class",
                          "View modules, filtered by domain": "View modules, filtered by domain",
                          "View all modules": "View all modules", "Run this configuration": "False"})

    def test_menu_remove_nonexistent_menuitem(self):
        """Test that removing a MenuItem not present in the Menu does not modify its contents."""
        test_menuitem = ec2rlcore.menu_item.MenuItem(row_left="Test row_left",
                                                     header="Test header",
                                                     helptext="Test helptext")
        original_length = len(self.menu)
        self.menu.remove(test_menuitem)
        self.assertEqual(original_length, len(self.menu))
        self.assertEqual(self.menu.get_items_dict_copy(),
                         {"Save and exit": "None",
                          "Configure global module arguments": "Configure global module arguments",
                          "View modules, filtered by class": "View modules, filtered by class",
                          "View modules, filtered by domain": "View modules, filtered by domain",
                          "View all modules": "View all modules", "Run this configuration": "False"})

    def test_menu_append_non_menuitem(self):
        """Test that appending a non-MenuItem doesn't modify its contents."""
        original_length = len(self.menu)
        self.menu.append("a")
        self.assertEqual(original_length, len(self.menu))
        self.assertEqual(self.menu.get_items_dict_copy(),
                         {"Save and exit": "None",
                          "Configure global module arguments": "Configure global module arguments",
                          "View modules, filtered by class": "View modules, filtered by class",
                          "View modules, filtered by domain": "View modules, filtered by domain",
                          "View all modules": "View all modules", "Run this configuration": "False"})
