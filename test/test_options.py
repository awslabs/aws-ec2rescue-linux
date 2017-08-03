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

"""Unit tests for "options" module."""
import configparser
import os
import sys
import unittest

import mock

import ec2rlcore.moduledir
import ec2rlcore.options

# builtins was named __builtin__ in Python 2 so accommodate the change for the purposes of mocking the open call
if sys.version_info >= (3,):
    builtins_name = "builtins"
else:
    builtins_name = "__builtin__"


class TestOptions(unittest.TestCase):
    """Testing class for "options" unit tests."""
    module_path = ""
    module = ""

    argv_backup = sys.argv
    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    if os.path.isdir(_callp):
        callpath = _callp
    else:
        callpath = os.path.split(_callp)[0]

    def setUp(self):
        """Setup the default options"""
        self.__subcommands = sorted(["run", "list", "help", "menu-config", "save-config", "upload", "version",
                                     "version-check", "software-check", "bug-report"])
        self.__meta_options = ["--config-file", "--url", "--upload-directory"]

    def tearDown(self):
        sys.argv = self.argv_backup

    def test_options_default_options(self):
        """Check that Options returns with no error and no subcommand set on default run."""
        sys.argv = ["ec2rl"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        self.assertIsNone(self.options.subcommand)

    def test_options_default_options_no_subcommands(self):
        """Check that Options returns with no error and subcommand is unset in a default run with no subcommand list."""
        sys.argv = ["ec2rl"]
        self.options = ec2rlcore.options.Options()
        self.assertIsNone(self.options.subcommand)

    def test_options_run_subcommand(self):
        """Check that run command is parsed correctly."""
        sys.argv = ["ec2rl", "run"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        self.assertEqual(self.options.subcommand, "run")

    def test_options_unknown_subcommand(self):
        """Test for proper failure when running unknown subcommand."""
        sys.argv = ["ec2rl", "badcommand"]
        with self.assertRaises(ec2rlcore.options.OptionsInvalidSubcommandError):
            self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)

    def test_options_argument_subcommand_key(self):
        """Test that additional subcommand args are processed correctly."""
        sys.argv = ["ec2rl", "help", "list"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        self.assertTrue("list" in self.options.global_args.keys())
        self.assertFalse(self.options.global_args["list"])

    def test_options_argument_nokey_value(self):
        """Test parsing of argument with "no" key."""
        sys.argv = ["ec2rl", "run", "--no=xyz"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        value = self.options.global_args["xyz"]
        self.assertEqual(value, "False")

    def test_options_argument_key_value(self):
        """Test parsing of argument with a value."""
        sys.argv = ["ec2rl", "run", "--abc=xyz"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        value = self.options.global_args["abc"]
        self.assertEqual(value, "xyz")

    def test_options_argument_key_novalue(self):
        """Test parsing of argument with no value."""
        sys.argv = ["ec2rl", "run", "--abc"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        value = self.options.global_args["abc"]
        self.assertEqual(value, "True")

    def test_options_argument_hyphenated_key_value(self):
        """Test parsing of a hyphenated argument with a value."""
        sys.argv = ["ec2rl", "run", "--abc-def=xyz"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        self.assertTrue("abcdef" in self.options.global_args.keys())
        self.assertEqual(self.options.global_args["abcdef"], "xyz")

    def test_options_argument_nonhyphenated_nonsubcommand(self):
        """Test parsing of an argument that isn't a subcommand is not prefixed with double hyphens."""
        sys.argv = ["ec2rl", "help", "tcptraceroute"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        self.assertTrue("tcptraceroute" in self.options.global_args.keys())
        self.assertEqual(self.options.global_args["tcptraceroute"], "")

    def test_options_invalid_argument(self):
        """Test invalid argument handling."""
        sys.argv = ["ec2rl", "run", "-abc=xyz"]
        with self.assertRaises(ec2rlcore.options.OptionsInvalidOptionError):
            self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)

    def test_options_notaninstance_true(self):
        """Test handling of --not-an-instance."""
        sys.argv = ["ec2rl", "run", "--not-an-instance"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        value = self.options.global_args["notaninstance"]
        self.assertTrue(value)

    def test_options_notaninstance_implied_false(self):
        """Test handling of notaninstance when unspecified."""
        sys.argv = ["ec2rl", "run"]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        value = self.options.global_args["notaninstance"]
        self.assertEqual(value, "False")

    def test_options_load_good_config(self):
        """Test that loading a good configuration file yields expected results."""
        configuration_path = os.path.join(self.callpath, "test/configurations/configuration.cfg")
        sys.argv = ["ec2rl", "run", "--config-file={}".format(configuration_path)]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        self.assertEqual(self.options.global_args["asdf"], "1234")
        self.assertEqual(self.options.per_module_args["arpcache"]["efgh"], "5678")

    def test_options_load_good_config_no_subcommand(self):
        """
        Test that loading a good configuration file with no subcommand and no subcommand provided via CLI args
        results in an unset subcommand.
        """
        configuration_path = os.path.join(self.callpath, "test/configurations/configuration.cfg")
        sys.argv = ["ec2rl", "--config-file={}".format(configuration_path)]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        self.assertEqual(self.options.global_args["asdf"], "1234")
        self.assertEqual(self.options.per_module_args["arpcache"]["efgh"], "5678")
        self.assertFalse(self.options.subcommand)

    def test_options_load_good_config_empty_section(self):
        """Test that loading a configuration file with an empty section doesn't create a corresponding dict key."""
        configuration_path = os.path.join(self.callpath, "test/configurations/empty_section_config.cfg")
        sys.argv = ["ec2rl", "run", "--config-file={}".format(configuration_path)]
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        self.assertEqual(self.options.global_args["asdf"], "1234")
        self.assertFalse("arpcache" in self.options.per_module_args)

    def test_options_load_empty_config(self):
        """Test that loading an empty configuration file yields expected results."""
        configuration_path = os.path.join(self.callpath, "test/configurations/empty_config.cfg")
        sys.argv = ["ec2rl", "run", "--config-file={}".format(configuration_path)]
        with self.assertRaises(ec2rlcore.options.OptionsInvalidConfigurationFile):
            self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)

    def test_options_load_malformed_config(self):
        """Test that attempting to load a non-existent configuration file yields expected results."""
        configuration_path = os.path.join(self.callpath, "test/configurations/junk_config.cfg")
        sys.argv = ["ec2rl", "run", "--config-file={}".format(configuration_path)]
        with self.assertRaises(ec2rlcore.options.OptionsInvalidConfigurationFile):
            self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)

    def test_options_load_invalid_subcommand(self):
        """
        Test that attempting to load configuration with an unsupport subcommand raises
        OptionsInvalidSubcommandConfigFileError.
        """
        configuration_path = os.path.join(self.callpath, "test/configurations/invalid_subcommand.cfg")
        sys.argv = ["ec2rl", "run", "--config-file={}".format(configuration_path)]
        with self.assertRaises(ec2rlcore.options.OptionsInvalidSubcommandConfigFileError):
            self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)

    def test_options_load_missing_config(self):
        """Test that attempting to load a non-existent configuration file yields expected results."""
        sys.argv = ["ec2rl", "run", "--config-file=asdf/123"]
        with self.assertRaises(ec2rlcore.options.OptionsInvalidConfigurationFile):
            self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)

    def test_options_write_config(self):
        """Test that attempting to write a config file yields expected results"""
        configuration_path = os.path.join(self.callpath, "test/configurations/test_write.cfg")
        sys.argv = ["ec2rl", "run"]
        module_path = os.path.join(self.callpath, "test/modules/mod.d")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        with mock.patch("{}.open".format(builtins_name), new_callable=mock.mock_open()) as open_mock:
            config = self.options.write_config(configuration_path, modules)
            self.assertIsInstance(config, configparser.ConfigParser)
            self.assertTrue(open_mock.called)

    def test_options_write_config_global_args(self):
        """Test that attempting to write a config with global args yields expected results."""
        configuration_path = os.path.join(self.callpath, "test/configurations/test_write.cfg")
        sys.argv = ["ec2rl", "run"]
        module_path = os.path.join(self.callpath, "test/modules/mod.d")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        self.options.global_args["period"] = "5"
        with mock.patch("{}.open".format(builtins_name), new_callable=mock.mock_open()) as open_mock:
            config = self.options.write_config(configuration_path, modules)
            self.assertIsInstance(config, configparser.ConfigParser)
            self.assertEqual(config["Global"]["period"], "5")
            self.assertTrue(open_mock.called)

    def test_options_write_config_per_module_args(self):
        """Test that attempting to write a config with per module args yields expected results."""
        configuration_path = os.path.join(self.callpath, "test/configurations/test_write.cfg")
        sys.argv = ["ec2rl", "run"]
        module_path = os.path.join(self.callpath, "test/modules/mod.d")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        # Test for module present in modules list
        self.options.per_module_args["atop"] = {}
        self.options.per_module_args["atop"]["times"] = "1"
        # Test for module not present in modules list
        self.options.per_module_args["test"] = {}
        self.options.per_module_args["test"]["times"] = "1"
        # Test for module named "Global"
        self.options.per_module_args["Global"] = {}
        self.options.per_module_args["Global"]["times"] = "1"
        with mock.patch("{}.open".format(builtins_name), new_callable=mock.mock_open()) as open_mock:
            config = self.options.write_config(configuration_path, modules)

            self.assertIsInstance(config, configparser.ConfigParser)
            self.assertEqual(config["atop"]["times"], "1")
            self.assertEqual(config["test"]["times"], "1")
            self.assertFalse("times" in config["Global"])
            self.assertTrue(open_mock.called)

    def test_options_write_config_named_global_module(self):
        """Test that attempting to write a config with named global module yields expected results."""
        configuration_path = os.path.join(self.callpath, "test/configurations/test_write.cfg")
        sys.argv = ["ec2rl", "run"]
        module_path = os.path.join(self.callpath, "test/modules/test_write_config_named_global_module/")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        self.options = ec2rlcore.options.Options(subcommands=self.__subcommands)
        # config = self.options.write_config(configuration_path, modules)
        with self.assertRaises(ec2rlcore.options.OptionsInvalidModuleName):
            self.options.write_config(configuration_path, modules)
