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
Options module

Functions:
    None

Classes:
    Options: dict-like object that holds the module arguments

Exceptions:
    OptionsError: base exception class for this module
    OptionsInvalidOptionError: raised when an unparsable argument is encountered
    OptionsInvalidSubcommandError: raised when an unsupported subcommand is encountered
    OptionsInvalidConfigurationFile: raised when trying to load data from an invalid configuration file
    OptionsInvalidModuleName: raised when an invalid or duplicate module name is encountered
    ArgParserWrapper: overrides argparse's built-in exception as ec2rl provides its own usage/help messages
"""
from __future__ import print_function

import argparse
import os
import re

try:
    # Python 3
    import configparser
except ImportError:  # pragma: no cover
    # Python 2
    import ConfigParser as configparser

from ec2rlcore.logutil import LogUtil


class Options(object):
    """
    Store the argument:value pairs and subcommand and provide the ability to
    save and load these values to/from a configuration file.

    Attributes:
        subcommand_list (list): the list of valid subcommands
        subcommand (str): the subcommand to be run
        per_module_args (dict): contains constraint:value pairs at a per module level
        global_args (dict): contains constraint:value pairs at the global level

    Methods:
        cmdline: parse the arguments ec2rl was called with
        load_config: load a ConfigParser configuration file and add its configuration to the Options object
        write_config: write the Options configuration to a ConfigParser configuration file
    """
    def __init__(self, subcommands=None):
        """
        Perform initial configuration of the object.

        Parameters:
            subcommands (list): the list of valid subcommands
        """
        self.logger = LogUtil.get_root_logger()
        self.parser = ArgParserWrapper()
        self.logger.debug("options.Options.__init__()")
        if subcommands is None:
            subcommands = []
        self.subcommand_list = subcommands
        self.subcommand = None
        self.classes_to_run = []
        self.domains_to_run = []
        self.per_module_args = {}
        self.global_args = {}
        self.cmdline()

    def cmdline(self, argv=None):
        """
        Parse the arguments provided to ec2rl and set the subcommand, handle any special arguments,
        and set the argument:value key pairs. Hyphens are removed to satisfy variable naming requirements.

        Parameters:
            argv (list): the arguments provided to ec2rl

        Returns:
            True (bool)
        """
        self.logger.debug("options.Options.cmdline({})".format(argv))
        # Process subcommands. With the exception of the --config_file variable, the only known arguments are
        # the subcommands. The remainder are unknown arguments and dynamically added below.
        self.logger.debug("subcommands:  {}".format(self.subcommand_list))
        self.parser.add_argument("subcommand", nargs="?")
        self.parser.add_argument("--config-file", dest="config_file")
        self.parser.add_argument("--no", nargs="?", default=None)
        known_args, unknown_args_list = self.parser.parse_known_args()
        known_args_dict = vars(known_args)

        for dynamic_arg in unknown_args_list:
            if dynamic_arg.startswith("--"):
                dynamic_arg = dynamic_arg.split("=")[0]
                self.parser.add_argument(dynamic_arg, action="store", default=True, nargs="?")
            elif "=" not in dynamic_arg and re.match("[a-zA-Z0-9]", dynamic_arg):
                self.parser.add_argument(dynamic_arg, action="store_const", const="")
            else:
                self.logger.debug("unknown command-line token '{}'".format(dynamic_arg))
                raise OptionsInvalidOptionError(dynamic_arg)

        # Parse and create a dict of the args
        parsed_arg_dict = vars(self.parser.parse_args())
        self.logger.debug("arguments:  {}".format(parsed_arg_dict))
        resultant_args_dict = {}

        # Remove known args that are not set (default to None)
        for key in known_args_dict.keys():
            if not known_args_dict[key]:
                del parsed_arg_dict[key]

        for key in parsed_arg_dict.keys():
            # If the "no" key has a value, handle the args.
            if key == "no" and parsed_arg_dict[key]:
                resultant_args_dict[parsed_arg_dict[key]] = "False"
            elif parsed_arg_dict[key] is None:
                parsed_arg_dict[key] = "True"
            # Remove underscores in the dict keys.
            resultant_args_dict[key.replace("_", "")] = parsed_arg_dict[key]

        # Populate global_args with the resultant key:value pairs
        for key in resultant_args_dict.keys():
            self.global_args[key] = resultant_args_dict[key]

        # If a subcommand was provided, verify it is valid
        if "subcommand" in parsed_arg_dict.keys() and parsed_arg_dict["subcommand"]:
            if parsed_arg_dict["subcommand"] in self.subcommand_list:
                self.subcommand = known_args_dict["subcommand"]
            else:
                raise OptionsInvalidSubcommandError(known_args.subcommand, re.sub(r"[\[\]]", "",
                                                                                  str(self.subcommand_list)))

        # Explicitly add notaninstance so it is always clear whether the config was run an instance or not in the
        # absence of this value being True
        if "notaninstance" not in self.global_args.keys():
            self.global_args["notaninstance"] = "False"

        # Load the config file, if specified. This will overwrite existing values in global_args.
        if "config_file" in parsed_arg_dict.keys():
            self.load_config(parsed_arg_dict["config_file"])
            # The configfile key pair should not be saved in the config file so remove it
            del self.global_args["configfile"]
            if "subcommand" in self.global_args.keys():
                if self.global_args["subcommand"] not in self.subcommand_list:
                    raise OptionsInvalidSubcommandConfigFileError(self.global_args["subcommand"],
                                                                  parsed_arg_dict["config_file"],
                                                                  re.sub(r"[\[\]]", "", str(self.subcommand_list)))
                else:
                    self.subcommand = self.global_args["subcommand"]

        self.logger.debug("...subcommand= {}".format(self.subcommand))
        return True

    def load_config(self, config_file):
        """
        Read in the configuration file and populate self.per_module_args from the sections and values.

        Parameters:
            config_file (str): the path to the configcarser configuration file

        Returns:
            None
        """
        self.logger.debug("ec2rlcore.options.Option.parse_config({})".format(config_file))

        config = configparser.ConfigParser()
        expanded_config_file = os.path.expanduser(os.path.expandvars(config_file))
        self.logger.debug("Config file path expanded to: '{}')".format(expanded_config_file))
        try:
            config.read(expanded_config_file)
        # UnicodeDecodeError is thrown when a binary file is read by configparser
        except UnicodeDecodeError:
            raise OptionsInvalidConfigurationFile(expanded_config_file)
        # ConfigParser.read() doesn't raise an exception for non-existent files so check that the action was successful
        if not config.sections():
            raise OptionsInvalidConfigurationFile(expanded_config_file)
        for section in config.sections():
            # Only add empty modules (those without constraint:value pairs)
            if config.options(section):
                # Load constraint:value pairs for all modules
                if section != "Global":
                    module_name = section
                    self.per_module_args[module_name] = {}
                    for option in config.options(module_name):
                        self.logger.debug("Adding [{}][{}] = {}".format(
                            module_name, option, config.get(module_name, option)))
                        self.per_module_args[module_name][option] = config.get(module_name, option)
                # Load global constraint:value pairs
                else:
                    for option in config.options(section):
                        self.logger.debug("Adding [{}] = {}".format(option, config.get(section, option)))
                        self.global_args[option] = config.get(section, option)
        return None

    def write_config(self, config_file, module_list):
        """
        Write a configuration file containing the data in self.per_module_args.

        Parameters:
            config_file (str): the path to the ConfigParser configuration file
            module_list (ModuleDir) : the list-like object of the modules

        Returns:
            config (ConfigParser): the resultant ConfigParser with the module sections
        """
        self.logger.debug("self.options.write_config({})".format(config_file))

        config = configparser.ConfigParser(allow_no_value=True)

        # Create a global section and add the global constraints
        self.logger.debug("Adding section: {}".format("Global"))
        config.add_section("Global")
        for constraint_name in self.global_args:
            constraint_value = self.global_args[constraint_name]
            self.logger.debug("Adding [Global] - {} = {}".format(constraint_name, constraint_value))
            config.set("Global", constraint_name, constraint_value)

        # Create a section for each module and add each module's constraints in comments
        for mod in module_list:
            # Global is reserved so skip a module of the same name
            try:
                # Create a section per module
                self.logger.debug("Adding section: {}".format(mod.name))
                config.add_section(mod.name)
                for value in mod.constraint["required"]:
                    key = "# (required) {} = value".format(value)
                    self.logger.debug("Adding [{}] - {}".format(mod.name, key))
                    config.set(mod.name, key)
                for value in mod.constraint["optional"]:
                    key = "# (optional) {} = value".format(value)
                    self.logger.debug("Adding [{}] - {}".format(mod.name, key))
                    config.set(mod.name, key)
                # Some modules do not require any arguments so leave a note stating such
                if not config.options(mod.name):
                    self.logger.debug("Adding [{}] - # none".format(mod.name))
                    config.set(mod.name, "# none")
            except configparser.DuplicateSectionError:
                raise OptionsInvalidModuleName()

        # If present, add the per-module args
        if self.per_module_args:
            self.logger.debug("Inside: 'if self.per_module_args'")
            for module_name in self.per_module_args:
                # Global is reserved so skip a module of the same name
                if module_name == "Global":
                    continue
                # If missing, add a section for the module
                if module_name not in config.sections():
                    self.logger.debug("Adding section: {}".format(module_name))
                    config.add_section(module_name)
                for constraint_name in self.per_module_args[module_name]:
                    constraint_value = self.per_module_args[module_name][constraint_name]
                    self.logger.debug("Adding [{}] - {} = {}".format(module_name, constraint_name, constraint_value))
                    config.set(module_name, constraint_name, constraint_value)
        # Save the configuration as a file
        expanded_config_file = os.path.expanduser(os.path.expandvars(config_file))
        self.logger.debug("Config file path expanded to: '{}')".format(expanded_config_file))
        with open(expanded_config_file, "w") as configfile:
            config.write(configfile)
        return config


class OptionsError(Exception):
    """Base class for exceptions in this module."""
    pass


class OptionsInvalidOptionError(OptionsError):
    """An unparsable argument was encountered."""
    def __init__(self, bad_option, *args):
        message = "Invalid Command line option '{}'.  Options should be in the format --abc or --abc=xyz".format(
            bad_option)
        super(OptionsInvalidOptionError, self).__init__(message, *args)


class OptionsInvalidSubcommandConfigFileError(OptionsError):
    """An unsupported subcommand was encountered in a configuration file."""
    def __init__(self, bad_subcommand, file_name, subcommands, *args):
        message = "Invalid Subcommand '{}' found in configuration file {}.  Valid subcommands are: {}.".format(
            bad_subcommand, file_name, subcommands)
        super(OptionsInvalidSubcommandConfigFileError, self).__init__(message, *args)


class OptionsInvalidSubcommandError(OptionsError):
    """An unsupported subcommand was encountered."""
    def __init__(self, bad_subcommand, subcommands, *args):
        message = "Invalid Subcommand '{}'.  Valid subcommands are: {}.".format(bad_subcommand, subcommands)
        super(OptionsInvalidSubcommandError, self).__init__(message, *args)


class OptionsInvalidConfigurationFile(OptionsError):
    """Exception raised when an invalid configuration file is encountered."""
    def __init__(self, file_name, *args):
        message = "Failed to load data from configuration file '{}'.".format(file_name)
        super(OptionsInvalidConfigurationFile, self).__init__(message, *args)


class OptionsInvalidModuleName(OptionsError):
    """An invalid module name is encountered. The edge case for this is a duplicate module name."""
    def __init__(self, *args):
        message = "Invalid module name. 'Global' is reserved."
        super(OptionsInvalidModuleName, self).__init__(message, *args)


class ArgParserWrapper(argparse.ArgumentParser):
    """An argparse error was encountered, but ec2rl will handle it differently."""
    def __init__(self):
        super(ArgParserWrapper, self).__init__(add_help=False)

    def error(self, message):
        """Override the built-in error function since ec2rl has its own usage/help messages."""
        pass
