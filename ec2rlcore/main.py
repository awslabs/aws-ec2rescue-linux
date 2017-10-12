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
Main module.

Functions:
    None

Classes:
    Main: Main, runnable driver for ec2rl

Exceptions:
    MainError: base error class for this module
    MainPrediagnosticFailure: raised when a prediagnostic check fails
    MainFileCopyError: raised when a file copy fails
    MainFileRemovalError: raised when removal of a file fails
    MainInvalidVolumeSpecificationError: raised when an invalid volume ID or Linux block device is specified
    MainDirectoryError: raised when a directory modification or creation fails
    MainMissingRequiredArgument: raised when a subcommand is missing a required argument
    MainVersionCheckTimeout: raised when a timeout occurs when trying to reach the VERSION S3 endpoint
"""
from __future__ import print_function
import datetime
import errno
import os
import platform
import re
import shutil
import sys
import logging

import ec2rlcore
import ec2rlcore.console_out
import ec2rlcore.constraint
import ec2rlcore.logutil
import ec2rlcore.moduledir
import ec2rlcore.options
import ec2rlcore.paralleldiagnostics
import ec2rlcore.prediag
import ec2rlcore.programversion
import ec2rlcore.s3upload

import requests
import yaml


class Main(object):
    """
    Main, runnable driver for ec2rl.

    Attribute:
        logger (Logger): logger object used to capture the different levels of logging message
        console (Logger): logger object accessible via LogUtil.get_direct_console_logger() to output messages to stdout
        directories (dict): contains all the various directory paths used by ec2rl
        constraint (Constraint): dict-like object containing the constraint key:value pairs
        _modules (ModuleDir): list-like object of the run modules
        _prediags (ModuleDir): list-like object of the prediagnostic modules
        _postdiags (ModuleDir): list-like object of the postdiagnostic modules
        subcommand (str): subcommand to be executed (e.g. run, list)
        options (Options): dict-like object of parsed command line arguments


    Methods:
        full_init: complete the lazy load of the modules
        _setup_write_paths: create the directory structure necessary for ec2rl to run
        _setup_environ: set environment variables to be passed to the modules
        module: returns _modules, finishing the lazy load as needed
        prediags returns _prediags, finishing the lazy load as needed
        postdiag: returns _postdiags, finishing the lazy load as needed
        get_help: returns the help message string for the given subcommand
        list: print the list of available, applicable modules the user can run
        help: print the help message for ec2rl or the specified items given in the args
        save_config: use the provided arguments to create a ConfigParser configuration file, configuration.cfg
        with all the module constraint:value pairs
        menu_config: use a menu system to create a ConfigParser configuration file, configuration.cfg
        __call__: run the subcommand calling getattr
        version: display the version and licensing information
        version_check: compares PROGRAM_VERSION against the upstream version and returns True if an update is available
        software_check: check for software that is required by modules but not installed
        bug_report: display version information relevant for inclusion in a bug report
        upload: upload a tarball of a directory to S3 using either a presigned URL or an AWS-support provided URL
        run: run one or more modules
        _run_prunemodules: determines whether each module should be run and removes modules that should not be run from
        the list of modules that will be run
        _run_backup: creates a backup of the type appropriate to the parsed arguments
        _run_prediagnostics: runs the prediagnostic modules
        _run_diagmodules_parallel: runs the diagnostic modules in parallel
        _run_postdiagnostics: runs the postdiagnostic modules
        _summary: prints summary statistics of the diagnostic execution as well as other related messages
    """

    # Implemented subcommands
    subcommands = sorted(["run", "list", "help", "menu-config", "save-config", "upload", "version", "version-check",
                          "software-check", "bug-report"])
    # Implemented meta options (long args)
    __meta_options = ["--config-file", "--url", "--upload-directory"]
    # Version number
    PROGRAM_VERSION = ec2rlcore.programversion.ProgramVersion("1.0.1")
    VERSION_ENDPOINT = "https://s3.amazonaws.com/ec2rescuelinux/VERSION"

    def __init__(self, debug=False, full_init=False):
        """Perform minimal configuration of the object."""
        self._write_initialized = False
        self._full_initialized = False

        # Empty initialization for heavier code paths which will be lazy executed when needed
        self._modules = None  # type: ec2rlcore.moduledir.ModuleDir
        self._prediags = None  # type: ec2rlcore.moduledir.ModuleDir
        self._postdiags = None  # type: ec2rlcore.moduledir.ModuleDir
        self._modules_need_init = True
        self._prediags_need_init = True
        self._postdiags_need_init = True

        self.pruned_modules = list()
        self.prune_stats = dict()

        self.logger = ec2rlcore.logutil.LogUtil.get_root_logger()

        self.console = ec2rlcore.logutil.LogUtil.set_direct_console_logger(logging.INFO)
        self.directories = {"WORKDIR": "/var/tmp/ec2rl"}

        # if called with relative paths, build absolute path off current-working directory
        _callp = sys.argv[0]
        if not os.path.isabs(_callp):
            _callp = os.path.abspath(_callp)

        # The modules directory neighbors the executable
        # (but the CWD/PWD will change, so we need a fully-specified path)
        self.directories["CALLPATH"] = os.path.split(_callp)[0]

        if "--debug" in sys.argv or debug:
            self.debug = True
            self.logger.setLevel(logging.DEBUG)
            self._setup_write_paths()
            ec2rlcore.logutil.LogUtil.set_debug_log_handler(os.sep.join((self.directories["RUNDIR"], "Debug.log")))
            self.logger.debug("ec2rlcore.Main.__init__()")
        else:
            self.debug = False
            self.logger.setLevel(logging.INFO)

        # Help is the default subcommand
        self.subcommand = "default_help"

        # Parse the commandline options and set the subcommand to be run, if it was specified as an argument
        self.options = ec2rlcore.options.Options(subcommands=Main.subcommands)

        self.constraint = ec2rlcore.constraint.Constraint()

        # If the user specified a subcommand use that instead of the default.
        if self.options.subcommand:
            self.subcommand = self.options.subcommand

        if full_init:
            self.full_init()

    def full_init(self):
        """Perform the rest of the init"""
        # Only full init once!
        if self._full_initialized:
            return True
        self._setup_write_paths()

        # Configure the main log file
        ec2rlcore.logutil.LogUtil.set_main_log_handler(os.sep.join((self.directories["RUNDIR"], "Main.log")))
        self.logger.debug("Added main log handler at {}".format(os.sep.join((self.directories["RUNDIR"], "Main.log"))))

        ec2rlcore.logutil.LogUtil.set_console_log_handler(logging.WARNING)
        self.logger.debug("Console logging for warning+ enabled")

        self._setup_environ()

        # Accessing the property will result in it being initialized
        self.logger.debug("Initialized {} 'prediag' module(s)".format(len(self.prediags)))
        self.logger.debug("Initialized {} 'run' module(s)".format(len(self.modules)))
        self.logger.debug("Initialized {} 'postdiag' module(s)".format(len(self.postdiags)))

        # Create the combined list of constraint:value pairs from all modules
        for mod in self.modules:
            self.constraint.update(mod.constraint.with_keys(["domain", "class", "distro", "software", "perfimpact"]))

        self.logger.debug("my subcommand = {}".format(self.subcommand))
        self.logger.debug("my constraints {}".format(self.constraint))
        self.logger.debug("my global_args {}".format(self.options.global_args))
        self._full_initialized = True

    def _setup_write_paths(self):
        """
        Create the directory structure necessary for ec2rl to run.

        Returns:
            True (bool)
        """
        if self._write_initialized:
            return True

        # Each Run gets its own directory to hold output files
        datetime_str = re.sub(":", "_", datetime.datetime.utcnow().isoformat())
        self.directories["RUNDIR"] = os.sep.join([self.directories["WORKDIR"], datetime_str])

        # Store log files in the mod_out directory under RUNDIR
        self.directories["LOGDIR"] = os.sep.join([self.directories["RUNDIR"], "mod_out"])

        # Store gathered output log files in gathered_out directory under RUNDIR
        self.directories["GATHEREDDIR"] = os.sep.join([self.directories["RUNDIR"], "gathered_out"])

        # Getting the datetime_str for compression purposes
        self.directories["SPECDIR"] = datetime_str

        # create working directory if it doesn't exist
        try:
            # Ensure the file is read/writeable by all users.
            # Prevents permission issues when executed by root/sudo then a regular user
            os.mkdir(self.directories["WORKDIR"], 0o777)
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise MainDirectoryError(self.directories["WORKDIR"])

        # create subdirectory for each tool run
        try:
            os.mkdir(self.directories["RUNDIR"])
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise MainDirectoryError(self.directories["RUNDIR"])

        # create the root subdirectory for the module logs
        try:
            os.mkdir(self.directories["LOGDIR"])
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise MainDirectoryError(self.directories["LOGDIR"])

        # Create a subdirectory for each module placement
        try:
            os.mkdir("{}/prediagnostic".format(self.directories["LOGDIR"]))
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise MainDirectoryError("{}/prediagnostic".format(self.directories["LOGDIR"]))

        try:
            os.mkdir("{}/run".format(self.directories["LOGDIR"]))
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise MainDirectoryError("{}/run".format(self.directories["LOGDIR"]))

        try:
            os.mkdir("{}/postdiagnostic".format(self.directories["LOGDIR"]))
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise MainDirectoryError("{}/postdiagnostic".format(self.directories["LOGDIR"]))

        # create subdirectory for the gathered output logs
        try:
            os.mkdir(self.directories["GATHEREDDIR"])
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise MainDirectoryError(self.directories["GATHEREDDIR"])

        self._write_initialized = True
        return True

    def _setup_environ(self):
        """
        Set environment variables to be passed to the modules.

        Returns:
            True (bool)
        """
        self.logger.debug("ec2rlcore.Main._setup_environ()")

        # WORKDIR: path to the root directory used for data capture from all executions
        # RUNDIR: path to the root directory for a particular execution
        # LOGDIR: directory inside RUNDIR that contains module logs
        # GATHEREDDIR: directory inside RUNDIR that contains files captured by the modules
        # SPECDIR: root directory name for a particular execution (date + time)
        os.environ["EC2RL_WORKDIR"] = self.directories["WORKDIR"]
        os.environ["EC2RL_RUNDIR"] = self.directories["RUNDIR"]
        os.environ["EC2RL_LOGDIR"] = self.directories["LOGDIR"]
        os.environ["EC2RL_GATHEREDDIR"] = self.directories["GATHEREDDIR"]
        os.environ["EC2RL_SPECDIR"] = self.directories["SPECDIR"]
        os.environ["EC2RL_CALLPATH"] = self.directories["CALLPATH"]
        if "perfimpact" in self.options.global_args and self.options.global_args["perfimpact"] == "true":
            os.environ["EC2RL_PERFIMPACT"] = "True"
        else:
            os.environ["EC2RL_PERFIMPACT"] = "False"

        return True

    @property
    def modules(self):
        """
        Finish lazy load of self._modules and setup classes_to_run and domains_to_run, if needed, then return
        self._modules.

        Returns:
             self._modules (ModuleDir): list-like object containing the run modules
        """
        if self._modules_need_init:
            self._modules = ec2rlcore.moduledir.ModuleDir("{}/mod.d".format(self.directories["CALLPATH"]))
            self._modules_need_init = False

            # Check if the user specified particular classes to run with --only-classes=
            # Default to all classes if not specified
            if "onlyclasses" in self.options.global_args.keys():
                for module_class in self.options.global_args["onlyclasses"].rsplit(","):
                    if module_class and module_class not in self.options.classes_to_run:
                        self.options.classes_to_run.append(module_class)
            else:
                self.options.classes_to_run = self.modules.classes

            # Check if the user specified particular domains to run with --only-domains=
            # Default to all domains if not specified
            if "onlydomains" in self.options.global_args.keys():
                for module_domain in self.options.global_args["onlydomains"].rsplit(","):
                    if module_domain and module_domain not in self.options.domains_to_run:
                        self.options.domains_to_run.append(module_domain)
            else:
                self.options.domains_to_run = self.modules.domains
        return self._modules

    @property
    def prediags(self):
        """
        Finish lazy load of self._prediags, if needed, then return self._prediags.

        Returns:
             self._prediags (ModuleDir): list-like object containing the prediagnostic modules
        """
        if self._prediags_need_init:
            self._prediags = ec2rlcore.moduledir.ModuleDir("{}/pre.d".format(self.directories["CALLPATH"]))
            self._prediags_need_init = False
        return self._prediags

    @property
    def postdiags(self):
        """
        Finish lazy load of self._prediags, if needed, then return self._postdiags.

        Returns:
             self._postdiags (ModuleDir): list-like object containing the postdiagnostic modules
        """
        if self._postdiags_need_init:
            self._postdiags = ec2rlcore.moduledir.ModuleDir("{}/post.d".format(self.directories["CALLPATH"]))
            self._postdiags_need_init = False
            self._postdiags_need_init = False
        return self._postdiags

    def get_help(self, help_arg=None):
        """
        Return the help message matching the given subcommand.

        Parameters:
            help_arg (str): the subcommand whose help message is to be returned

        Returns:
            (str): the help message for the specified subcommand
        """
        with open(self.directories["CALLPATH"] + "/ec2rlcore/help.yaml") as helpfile:
            helpmessages = yaml.load(helpfile)

        help_dict = {
            "list": helpmessages["list_help"],
            "run": helpmessages["run_help"],
            "help": helpmessages["help_help"],
            "menu-config": helpmessages["menu_config_help"],
            "save-config": helpmessages["save_config_help"],
            "upload": helpmessages["upload_help"],
            "version": helpmessages["version_help"],
            "version-check": helpmessages["version_check_help"],
            "software-check": helpmessages["software_check_help"],
            "bug-report": helpmessages["bug_report_help"]
        }

        # If the given subcommand is valid then return the matching help message
        if help_arg in help_dict.keys():
            help_message = str(help_dict[help_arg])
        # If the given subcommand is not a supported subcommand then return a brief help/error message.
        elif self.subcommand == "default_help":
            help_message = helpmessages["help_header"]
            help_message += "\nec2rl: missing subcommand operand"
        else:
            help_message = helpmessages["help_header"]
            help_message += "\n"
            for subcommand in Main.subcommands:
                help_message += str(help_dict[subcommand])
                help_message += "\n"
            help_message += helpmessages["help_footer"]
        return help_message

    def list(self):
        """
        Print the list of available, applicable modules the user can run.

        Returns:
            True (bool)
        """
        self.logger.debug("ec2rlcore.Main.list()")
        print("Here is a list of available modules that apply to the current host:\n")
        print("\033[4m" + "  " + "{:20.18}{:10.8}{:13.11}{:77.75}".format("Module Name", "Class", "Domain",
                                                                          "Description") + "\033[0m")
        for mod in self.modules:
            if mod.applicable \
                    and set(mod.constraint["domain"]).intersection(self.options.domains_to_run) \
                    and set(mod.constraint["class"]).intersection(self.options.classes_to_run):
                print(mod.list)
        print("\n *Requires sudo/root to run")
        print("\n +Requires --perfimpact=true to run (Can potentially cause performance impact)")
        print("\n Classes come in three types: Diagnose, with success/fail/warn conditions determined by module.")
        print("\n Gather, which creates a copy of a local file for inspection. Collect, which collects command output")
        print("\n Domains are defined per module and refer to the general area of investigation for the module.")
        print("\nTo see module help, you can run:\n")
        print("ec2rl help [MODULEa ... MODULEx]")
        print("ec2rl help [--only-modules=MODULEa ... MODULEx] [--only-domains=DOMAINa ... DOMAINx]")
        return True

    def help(self):
        """
        Print the help message for ec2rl or the specified items given in the args.

        Returns:
            True (bool)
        """
        self.logger.debug("ec2rlcore.Main.help()")
        args_to_help = []
        output = ""
        self.full_init()

        # There are three ways to specify modules
        # Option one
        # ec2rl help --only-modules=telnetport
        if "onlymodules" in self.options.global_args:
            args_to_help = [mod_name for mod_name in self.options.global_args["onlymodules"].rsplit(",")]
        # Option two
        # ec2rl help --only-domains=net
        elif "onlydomains" in self.options.global_args:
            # Build the list of modules that match the domains given
            for this_domain in self.options.domains_to_run:
                if this_domain in self.modules.domain_map.keys():
                    for module_obj in self.modules.domain_map[this_domain]:
                        args_to_help.append(module_obj.name)
        # Option three
        # ec2rl help --only-classes=diagnose
        elif "onlyclasses" in self.options.global_args:
            for this_class in self.options.classes_to_run:
                if this_class in self.modules.class_map.keys():
                    for module_obj in self.modules.class_map[this_class]:
                        args_to_help.append(module_obj.name)
        # Or option four
        # ec2rl help telnetport ex
        elif len(sys.argv) >= 3:
            for arg_num in range(2, len(sys.argv)):
                # Filter out the arg if it isn't a subcommand or module name
                if sys.argv[arg_num] in self.subcommands or sys.argv[arg_num] in self.modules.name_map.keys():
                    args_to_help.append(sys.argv[arg_num])

        # Represents whether any of the args been matched to a module or subcommand
        match = False
        for arg in args_to_help:
            # Only print two newlines for matches after the first
            if match:
                output += "\n\n"
            # Handle cases where the arg is a subcommand
            if arg in self.options.subcommand_list:
                match = True
                output += self.get_help(arg)
            # Handle cases where the arg is a module name
            elif arg in self.modules.name_map.keys():
                match = True
                output += self.modules.name_map[arg].help

        # If neither modules nor subcommands match then use the default help/doc message
        if not output:
            # Default help
            output = self.get_help()

        print(output)
        return True

    def save_config(self):
        """
        Add each module's constraints and any parsed arguments to a ConfigParser object and create a configuration
        file from this object.

        Returns:
            True (bool):
        """
        self.full_init()
        self.logger.debug("ec2rlcore.Main.save_config()")

        config_file = os.sep.join((self.directories["RUNDIR"], "configuration.cfg"))
        self.options.write_config(config_file, self.modules)
        ec2rlcore.dual_log("\n----------[Configuration File]----------\n")
        ec2rlcore.dual_log("Configuration file saved:")
        ec2rlcore.dual_log(config_file)

        return True

    def menu_config(self):
        """
        Present the user with a curses-driven menu system for setting individual module options then create
        a configuration file using this data and save_config().
        """
        try:
            import curses
        except ImportError:  # pragma: no coverage
            print("ERROR:\tMissing Python module 'curses'.")
            print("\tPlease install this module and rerun ec2rl")
            sys.exit(1)

        import ec2rlcore.menu_item
        import ec2rlcore.menu_config

        self.full_init()
        self.logger.debug("ec2rlcore.Main.menu_config()")

        # "Global" is reserved remove a module using that name
        if "Global" in self.modules.name_map.keys():
            self.modules.remove(self.modules.name_map["Global"])

        # Create a menu-compatible OrderedDict from the data in self.modules
        the_menu = ec2rlcore.menu_config.get_menu_config(self.modules)
        the_menu()

        # Copy the data entered into module_config back into options
        module_menu = the_menu["View all modules"]
        for module_name in module_menu.get_item_keys():
            # Loop over the keys and remove any key:value pairs where the value is empty (unconfigured)
            # This is two steps because we don't want to mutate the dict while iterating it
            # Get the list of keys that need to be removed
            keys_to_remove = []
            for key in module_menu[module_name].get_item_keys():
                if (isinstance(module_menu[module_name][key], ec2rlcore.menu_item.TextEntryItem)
                        and not module_menu[module_name][key].get_value()) \
                        or isinstance(module_menu[module_name][key], ec2rlcore.menu_item.ExitItem):
                    keys_to_remove.append(key)
            # Delete each key whose value is empty
            for key in keys_to_remove:
                module_menu[module_name].remove(module_menu[module_name][key])
            # Set the module's argument dict to point to the new OrderedDict
            self.options.per_module_args[module_name] = module_menu[module_name].get_items_dict_copy()

        # Add any new global key/value pairs to self.options.global_args, but skip items with empty values
        global_menu = the_menu["Configure global module arguments"]
        for key in global_menu.get_item_keys():
            if isinstance(global_menu[key], (ec2rlcore.menu_item.ToggleItem, ec2rlcore.menu_item.TextEntryItem)) \
                    and global_menu[key].get_value():
                self.options.global_args[key] = global_menu[key].get_value()

        def update_only_global_arg(item_name):
            """
            Helper function to update the only-* global arg values.

            Parameters:
                item_name (str): RHS of the hyphenated global_args key (e.g. classes in only-classes)

            Returns:
                (bool): represents whether an update was made
            """
            num_items_to_run = 0
            str_items_to_run = ""
            for item in global_menu["only-{}".format(item_name)].get_items():
                if item.get_value() == "True":
                    num_items_to_run += 1
                    if not str_items_to_run:
                        str_items_to_run = item.row_left
                    else:
                        str_items_to_run = ",".join((str_items_to_run, item.row_left))
            if item_name == "modules" and 0 < num_items_to_run < len(self.modules) \
                    or item_name != "modules" and num_items_to_run < len(getattr(self.modules, item_name)):
                self.options.global_args["only{}".format(item_name)] = str_items_to_run
            else:
                return False
            return True

        update_only_global_arg("classes")
        update_only_global_arg("domains")
        update_only_global_arg("modules")

        # The subcommand key is set to "menuconfig" so change it to "run"
        self.options.global_args["subcommand"] = "run"

        # If the user selected "Run" from the menu then run the current configuration
        if the_menu["Run this configuration"].get_value():
            self.subcommand = "run"
            self()
        # If the user did not select "Run" from the menu then just save the configuration
        else:
            # Create the actual configuration file
            # Since the work is done in-place on per_module_args, a simple function call is all that is required
            return self.save_config()

    def __call__(self, subcommand=None):
        """
        Call the subcommand function via getattr.

        Parameters:
            subcommand: subcommand to be executed (e.g. run, list)

        Returns:
            rv: return value of the subcommand function that is executed via getattr
        """
        self.logger.debug("ec2rlcore.Main.__call__()")
        if not subcommand and self.subcommand == "default_help":
            subcommand = "help"
        elif not subcommand:
            subcommand = self.subcommand
        # Replace the hyphens so the subcommand matches its method name
        subcommand = subcommand.replace("-", "_")
        return getattr(self, subcommand)()

    def version(self):
        """Print the version and licensing information and return True."""
        print("ec2rl {}".format(self.PROGRAM_VERSION))
        print("Copyright 2016-2017 Amazon.com, Inc. or its affiliates. All rights reserved.")
        print("This software is distributed under the Apache License, Version 2.0.")
        print("")
        print("This file is distributed on an \"AS IS\" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, "
              "either express or implied.")
        return True

    def version_check(self):
        """
        Get the current upstream version, compare against this version, inform the user whether an update is available,
        and return True.
        """
        try:
            upstream_version = ec2rlcore.programversion.ProgramVersion(requests.get(self.VERSION_ENDPOINT).text.strip())
        except requests.exceptions.Timeout:
            raise MainVersionCheckTimeout()

        print("Running version:  {}".format(self.PROGRAM_VERSION))
        print("Upstream version: {}".format(upstream_version))
        if upstream_version > self.PROGRAM_VERSION:
            print("An update is available.")
            return True
        else:
            print("No update available.")
            return False

    def software_check(self):
        """
        Check for software that is not installed but is required for a module, and inform the user on details about how
        to obtain it if needed and return True.
        """
        packages_needed = set()
        for mod in self.modules:
            for software_constraint in iter(mod.constraint["software"]):
                if not ec2rlcore.prediag.which(software_constraint):
                    packages_needed.update(set(mod.package))

        packages_needed = [package for package in packages_needed if package]
        if len(packages_needed) > 0:
            print("One or more software packages required to run all modules are missing.\n"
                  "Information regarding these software packages can be found at the specified URLs below.\n")
            for package in packages_needed:
                modules = ",".join([mod.name for mod in self.modules.package_map[package]])
                try:
                    package_name, package_link = package.split()
                except ValueError:
                    raise MainSoftwareCheckPackageParsingFailure(package, modules)
                print("{}: {}".format("Package-Name", package_name))
                print("{}: {}".format("Package-URL", package_link))
                print("{}: {}".format("Affected-Modules", modules))
                print("")
        else:
            print("All test software requirements have been met.")
        return True

    def bug_report(self):
        """Print version information relevant for inclusion in a bug report and return True."""
        print("ec2rl {}".format(self.PROGRAM_VERSION))
        print("{}, {}".format(ec2rlcore.prediag.get_distro(), platform.release()))
        print("Python {}, {}".format(platform.python_version(), sys.executable))
        return True

    def upload(self):
        """
        Inspect the global_args and, if the url and upload directory were specified then tar the directory and upload
        the resulting tarball to S3 using the provided url.

        Returns:
            True (bool): returns True if the function completes.
        """
        if "uploaddirectory" not in self.options.global_args.keys():
            raise MainMissingRequiredArgument("The upload subcommand requires --upload-directory")

        tgz_filename = "ec2rl-" + \
                       os.path.basename(os.path.normpath(self.options.global_args["uploaddirectory"])) + \
                       ".tgz"

        if "supporturl" in self.options.global_args.keys():
            presigned_url = ec2rlcore.s3upload.get_presigned_url(self.options.global_args["supporturl"], tgz_filename)
        elif "presignedurl" in self.options.global_args.keys():
            presigned_url = self.options.global_args["presignedurl"]
        else:
            raise MainMissingRequiredArgument("The upload subcommand requires either --support-url or --presigned-url")

        # Ensure the ssl module is a sufficiently high enough version to allow the upload to succeed.
        # This check is placed here, rather than earlier, to let all the arg syntax checking to do its job first.
        try:
            from ssl import HAS_SNI
        except ImportError:
            raise MainUploadMissingSNISupport

        try:
            expanded_uploaddirectory = os.path.expanduser(
                os.path.expandvars(
                    self.options.global_args["uploaddirectory"]))
            ec2rlcore.s3upload.make_tarfile(tgz_filename, expanded_uploaddirectory)
            ec2rlcore.s3upload.s3upload(presigned_url, tgz_filename)
        finally:
            # Always delete the temporary file created
            try:
                os.remove(tgz_filename)
            except OSError:
                raise MainFileRemovalError(tgz_filename)

        return True

    def run(self):
        """
        Start the diagnostics run.

        1. Determine what modules can be run.
        2. Copy functions.bash to WORKDIR
        3. "cd" to WORKDIR
        4. Generate the run config
        5. Setup logging for Main.log
        6. Run prediagnostics
        7. Prune modules not selected or not meeting constraints
        8. Run all specified modules that are still applicable after constraint and prediagnostic checking

        Returns:
            True (bool)
        """
        self.logger.debug("ec2rlcore.Main.run()")
        self.full_init()

        # Move functions.bash to WORKDIR
        _source = os.sep.join([self.directories["CALLPATH"], "functions.bash"])
        _dest = os.sep.join([self.directories["RUNDIR"], "functions.bash"])
        try:
            shutil.copyfile(_source, _dest)
        # This is typically OSError, but can also be IOError or SameFileError depending upon the version of Python
        # Since the actual Exception is variable, catch any Exception
        except Exception:
            raise MainFileCopyError(_source, _dest)

        # Change current working directory
        os.chdir(self.directories["RUNDIR"])

        # Only run the backup if the system is an instance
        if self.options.global_args["notaninstance"] == "False":
            self._run_backup()

        self._run_prediagnostics()

        # Comparison of constraints to determine run/diag modules that can run
        self.modules.validate_constraints_have_args(
            options=self.options, constraint=self.constraint, without_keys=["software",
                                                                            "distro",
                                                                            "sudo",
                                                                            "requires_ec2"])

        self._run_prunemodules()
        # write-out the Configuration for this run to a file
        self.save_config()

        ec2rlcore.dual_log("\n-------------[Output  Logs]-------------\n")
        ec2rlcore.dual_log("The output logs are located in:")
        ec2rlcore.dual_log(self.directories["RUNDIR"])

        # Parallel is now the default and only diagnostic module execution path.
        # Setting concurrency=1 will simulate the serial execution mode by only running with one worker
        self._run_diagmodules_parallel()

        self._run_postdiagnostics()
        return True

    def _run_prunemodules(self):
        """
        Review the modules and set the applicable and whyskipping attributes to indicate whether the module should
        be run. Once complete, remove any non-applicable modules from the module list so that they are not run.
        """
        # Check if the user specified particular modules to run with --only-modules=
        if "onlymodules" in self.options.global_args:
            mods_to_run = [mod_name for mod_name in self.options.global_args["onlymodules"].rsplit(",")]
        # If the user didn't specify modules with --only-modules then run all modules
        else:
            mods_to_run = "all"
        self.logger.debug("mods_to_run={}".format(mods_to_run))

        prune_list = []
        for mod in self.modules:
            prune = False
            # If the module is supposed to run per the user's args, perform the additional prediagnostic checks
            if (mods_to_run == "all" or mod.name in mods_to_run) \
                    and set(mod.constraint["domain"]).intersection(self.options.domains_to_run) \
                    and set(mod.constraint["class"]).intersection(self.options.classes_to_run):
                # Flag the module for removal if validate_constraints_have_args found missing args (constraints)
                if not mod.applicable:
                    prune = True
                # Flag the module for removal if the module requires the system be an EC2 instance and
                # it is not an instance
                elif next(iter(mod.constraint["requires_ec2"])) == "True" \
                        and self.options.global_args["notaninstance"] == "True":
                    mod.whyskipping = "Module requires system be an EC2 instance."
                    prune = True
                # Flag the module for removal if it is not applicable to the system's detected distro
                elif os.environ["EC2RL_DISTRO"] not in list(mod.constraint["distro"]):
                    mod.whyskipping = "Not applicable to this distro."
                    prune = True
                # Flag the module for removal if performance impacting but no okay given
                elif next(iter(mod.constraint["perfimpact"])) == "True" and os.environ["EC2RL_PERFIMPACT"] == "False":
                    mod.whyskipping = "Requires performance impact okay, but not given."
                    prune = True
                # Flag the module for removal if it requires root/sudo but this is not executing as such
                elif next(iter(mod.constraint["sudo"])) == "True" and os.environ["EC2RL_SUDO"] == "False":
                    mod.whyskipping = "Requires sudo access, but not executing as root."
                    prune = True
            # If the module isn't supposed to run, determine how it was excluded by the user's args
            else:
                prune = True
                # Flag the module for removal of it was not specified or implied
                if mods_to_run != "all" and mod.name not in mods_to_run:
                    mod.whyskipping = "Not specified to run."
                # Flag the module for removal if its domain was not specified or implied
                elif not set(mod.constraint["domain"]).intersection(self.options.domains_to_run):
                    mod.whyskipping = "Not in specified domain to run."
                # else is equivalent of "not set(mod.constraint["class"]).intersection(self.options.classes_to_run):"
                else:
                    mod.whyskipping = "Not in specified class to run."

            # Check the software constraints against what can be found in PATH and is executable by this user, but
            # don't bother checking these if the module is already flagged for removal
            if not prune:
                for software_constraint in iter(mod.constraint["software"]):
                    if not ec2rlcore.prediag.which(software_constraint, mode=os.X_OK):
                        mod.whyskipping = "Requires missing/non-executable software '{}'.".format(
                            software_constraint)
                        prune = True

            # Create the list of modules to be removed
            if prune:
                self.logger.info("module {}/{}: Skipping. Reason: {}".format(mod.placement, mod.name, mod.whyskipping))
                prune_list.append(mod)
            else:
                self.logger.info("module {}/{}: Passed prediagnostics validation.".format(mod.placement, mod.name))

        # If module is flagged for pruning, add to the pruned list and remove from main module list
        for mod in prune_list:
            self._prune_module(mod)

    def _prune_module(self, mod):
        # Only collecting stats on the skip reasons we want to actually display

        if mod.whyskipping.startswith("Requires performance impact okay, but not given."):
            self._add_to_prune_stats(ec2rlcore.module.SkipReason.PERFORMANCE_IMPACT)
        elif mod.whyskipping.startswith("Requires sudo access, but not executing as root."):
            self._add_to_prune_stats(ec2rlcore.module.SkipReason.REQUIRES_SUDO)
        elif mod.whyskipping.startswith("Requires missing/non-executable software"):
            self._add_to_prune_stats(ec2rlcore.module.SkipReason.MISSING_SOFTWARE)
        elif mod.whyskipping.startswith("missing value for required argument"):
            self._add_to_prune_stats(ec2rlcore.module.SkipReason.MISSING_ARGUMENT)

        self.pruned_modules.append(mod)
        self.modules.remove(mod)

    def _add_to_prune_stats(self, reason, count=1):
        if reason not in self.prune_stats:
            self.prune_stats[reason] = 0
        self.prune_stats[reason] += count

    def _run_backup(self):
        """
        Runs the backup based on flags used

        Returns:
            None
        """
        import ec2rlcore.awshelpers
        import ec2rlcore.backup

        # Catch exceptions raising up from AWS creds/boto/etc configuration
        ec2rlcore.dual_log("\n-----------[Backup  Creation]-----------\n")
        # Creates an image of the current instance
        if "backup" in self.options.global_args and self.options.global_args["backup"] == "ami":
            ec2rlcore.backup.create_image(ec2rlcore.awshelpers.get_instance_id())
        # Creates snapshots of all attached volumes
        elif "backup" in self.options.global_args and self.options.global_args["backup"] == "allvolumes":
            ec2rlcore.backup.create_all_snapshots(ec2rlcore.awshelpers.get_volume_ids())
        elif "backup" in self.options.global_args:
            for volume_name in self.options.global_args["backup"].rsplit(","):
                if "vol" in volume_name:
                    ec2rlcore.backup.snapshot(volume_name)
                else:
                    ec2rlcore.dual_log("Improper specification of volumes. Please verify you have specified a volume"
                                       " such as vol-xxxxx.")
                    raise MainInvalidVolumeSpecificationError(volume_name)
        else:
            ec2rlcore.dual_log("No backup option selected. Please consider backing up your volumes or instance")
        return True

    def _run_prediagnostics(self):
        # Start prediagnostics
        self.logger.info("----------------------------------------")
        self.logger.info("BEGIN PREDIAGNOSTICS")
        self.logger.info("----------------------------------------")

        # Get the system config using the functions in the prediag module
        # Export these variables for the modules to use
        os.environ["EC2RL_SUDO"] = str(ec2rlcore.prediag.check_root())
        os.environ["EC2RL_DISTRO"] = ec2rlcore.prediag.get_distro()
        os.environ["EC2RL_NET_DRIVER"] = ec2rlcore.prediag.get_net_driver()

        if self.options.global_args["notaninstance"] == "True":
            os.environ["EC2RL_VIRT_TYPE"] = "non-virtualized"
            self.logger.info("prediagnostic/verify_metadata: not an instance; skipping")
        # Prediagnostic checks that rely on the system being an EC2 instance go here
        else:
            if ec2rlcore.prediag.verify_metadata():
                self.logger.info("prediagnostic/verify_metadata: can reach metadata server")
            else:
                ec2rlcore.dual_log("prediagnostic/verify_metadata: cannot reach metadata server")
                raise MainPrediagnosticFailure("metadata server inaccessible")
            os.environ["EC2RL_VIRT_TYPE"] = ec2rlcore.prediag.get_virt_type()

        # Run each prediagnostic module
        for mod in self.prediags:
            if mod.applicable:
                self.logger.info("module {}/{}: Running".format(mod.placement, mod.name))
                self.logger.debug("module {}/{}: applicable = True".format(mod.placement, mod.name))
                module_logger = ec2rlcore.logutil.LogUtil.create_module_logger(mod, self.directories["LOGDIR"])
                module_logger.info(mod.run(options=self.options))
                if mod.run_status == "FAILURE":
                    raise MainPrediagnosticFailure(mod.run_summary)

            else:
                self.logger.info("module {}/{}: Skipping. Reason: {}".format(mod.placement, mod.name, mod.whyskipping))
                self.logger.debug("module '{}': skipping: {}".format(mod.name, mod.whyskipping))
        return True

    def _run_diagmodules_parallel(self):
        """
        Run the selected diagnostic modules in parallel.

        Returns:
            (int): Count of modules run
        """
        # If concurrency arg is set, is a number, and is greater than 0
        if "concurrency" in self.options.global_args and self.options.global_args["concurrency"].isdigit():
            # Concurrency has a minimum of 1.  If arg concurrency is less than 1, floor at 1
            concurrency = max(1, int(self.options.global_args["concurrency"]))
        else:
            # Default concurrency level is set here:
            concurrency = 10

        ec2rlcore.dual_log("\n--------------[Module Run]--------------\n")

        # Sorting modules by class to attempt a consistent run order of classes
        self.modules.sort(key=lambda mod: mod.constraint["class"][0])

        modules_executed = ec2rlcore.paralleldiagnostics.parallel_run(self.modules,
                                                                      self.directories["LOGDIR"],
                                                                      concurrency=concurrency,
                                                                      options=self.options)

        ec2rlcore.dual_log("")
        self._summary()
        return modules_executed

    def _run_postdiagnostics(self):
        """
        Run the selected diagnostic modules in self.modules.

        Returns:
            (bool): True if there were any applicable modules to run
        """
        # Start postdiagnostics
        self.logger.info("----------------------------------------")
        self.logger.info("BEGIN POSTDIAGNOSTICS")
        self.logger.info("----------------------------------------")
        # Run each prediagnostic module
        for mod in self.postdiags:
            if mod.applicable:
                self.logger.info("module {}/{}: Running".format(mod.placement, mod.name))
                self.logger.debug("module {}/{}: applicable = True".format(mod.placement, mod.name))
                module_logger = ec2rlcore.logutil.LogUtil.create_module_logger(mod, self.directories["LOGDIR"])
                module_logger.info(mod.run(options=self.options))
            else:
                self.logger.info("module {}/{}: Skipping. Reason: {}".format(mod.placement, mod.name, mod.whyskipping))
                self.logger.debug("module '{}': skipping: {}".format(mod.name, mod.whyskipping))
        return True

    def _summary(self):
        """Print the summary of diagnostic execution."""
        # Determine the execution results for the "diagnose" class of modules
        diagnose_successes = 0
        diagnose_failures = 0
        diagnose_warnings = 0
        diagnose_unknowns = 0
        if "diagnose" in self.modules.class_map.keys():
            ec2rlcore.dual_log("\n----------[Diagnostic Results]----------\n")
            for module_obj in self.modules.class_map["diagnose"]:
                if module_obj.run_status == "SUCCESS":
                    diagnose_successes += 1
                elif module_obj.run_status == "FAILURE":
                    diagnose_failures += 1
                elif module_obj.run_status == "WARN":
                    diagnose_warnings += 1
                elif module_obj.run_status == "UNKNOWN":
                    diagnose_unknowns += 1

            # Sort the list by the run_status string so that warnings, successes, etc are grouped.
            for module_obj in sorted([module_obj for module_obj in self.modules.class_map["diagnose"]],
                                     key=lambda mod: mod.run_status):
                ec2rlcore.dual_log("{:32} {}".format(
                    "module " + module_obj.placement + "/" + module_obj.name, module_obj.run_summary))
                for detail in module_obj.run_status_details:
                    ec2rlcore.dual_log("{:32} {}".format(" ", detail))

        # Output the execution results
        ec2rlcore.dual_log("\n--------------[Run  Stats]--------------\n")
        ec2rlcore.dual_log("{:32} {}".format("Total modules run:", len(self.modules)))
        if len(self.modules) > 0:
            for class_name in self.modules.class_map.keys():
                ec2rlcore.dual_log("{:32} {}".format("'{}' modules run:".format(class_name),
                                                     len(self.modules.class_map[class_name])))
                if class_name == "diagnose":
                    ec2rlcore.dual_log("{:32} {}".format("    successes:", diagnose_successes))
                    ec2rlcore.dual_log("{:32} {}".format("    failures:", diagnose_failures))
                    ec2rlcore.dual_log("{:32} {}".format("    warnings:", diagnose_warnings))
                    ec2rlcore.dual_log("{:32} {}".format("    unknown:", diagnose_unknowns))

        if len(self.prune_stats) > 0:
            ec2rlcore.dual_log("\n{:32} {:<4} | {:<8} | {:<10} | {:<11}".format(
                "Modules not run due to missing:", "sudo", "software", "parameters", "perf-impact"))
            ec2rlcore.dual_log("{:32} {:>4} | {:>8} | {:>10} | {:>11}"
                               .format("",
                                       self.prune_stats.get(ec2rlcore.module.SkipReason.REQUIRES_SUDO, 0),
                                       self.prune_stats.get(ec2rlcore.module.SkipReason.MISSING_SOFTWARE, 0),
                                       self.prune_stats.get(ec2rlcore.module.SkipReason.MISSING_ARGUMENT, 0),
                                       self.prune_stats.get(ec2rlcore.module.SkipReason.PERFORMANCE_IMPACT, 0)))

        ec2rlcore. dual_log("\n----------------[NOTICE]----------------\n")
        ec2rlcore.dual_log("Please note, this directory could contain sensitive data depending on modules run! Please"
                           " review its contents!")
        ec2rlcore.dual_log("\n----------------[Upload]----------------\n")
        ec2rlcore.dual_log("You can upload results to AWS Support with the following, or run 'help upload' for details"
                           " on using an S3 presigned URL:\n")
        if os.environ["EC2RL_SUDO"] == "False":
            ec2rlcore.dual_log("./ec2rl upload --upload-directory={} --support-url=\"URLProvidedByAWSSupport\" \n".
                               format(self.directories["RUNDIR"]))
        elif os.environ["EC2RL_SUDO"] == "True":
            ec2rlcore.dual_log("sudo ./ec2rl upload --upload-directory={} --support-url=\"URLProvidedByAWSSupport\" \n".
                               format(self.directories["RUNDIR"]))
        ec2rlcore.dual_log("The quotation marks are required, and if you ran the tool with sudo, you will also need to"
                           " upload with sudo.")
        ec2rlcore.dual_log("\n---------------[Feedback]---------------\n")
        ec2rlcore.dual_log("We appreciate your feedback. If you have any to give, please visit:")
        if self.options.global_args["notaninstance"] == "True":
            ec2rlcore.dual_log("https://aws.au1.qualtrics.com/jfe1/form/SV_3KrcrMZ2quIDzjn?InstanceID={}&Version={}\n".
                               format("not_an_instance", self.PROGRAM_VERSION))
        else:
            ec2rlcore.dual_log("https://aws.au1.qualtrics.com/jfe1/form/SV_3KrcrMZ2quIDzjn?InstanceID={}&Version={}\n".
                               format(ec2rlcore.awshelpers.get_instance_id(), self.PROGRAM_VERSION))
        return True


class MainError(Exception):
    """Base class for exceptions in this module."""
    pass


class MainPrediagnosticFailure(MainError):
    """A prediagnostic check failed."""
    def __init__(self, error_message, *args):
        message = "Failed prediagnostic check: {}".format(error_message)
        super(MainPrediagnosticFailure, self).__init__(message, *args)


class MainFileCopyError(MainError):
    """A file copy failed."""
    def __init__(self, source, destination, *args):
        message = "Failed to copy necessary file '{}' to '{}'".format(source, destination)
        super(MainFileCopyError, self).__init__(message, *args)


class MainFileRemovalError(MainError):
    """Removal of a file failed."""
    def __init__(self, filename, *args):
        message = "Failed to remove file '{}'.".format(filename)
        super(MainFileRemovalError, self).__init__(message, *args)


class MainInvalidVolumeSpecificationError(MainError):
    """An invalid EBS volume ID/Linux block device specified."""
    def __init__(self, error_message, *args):
        message = "Invalid EBS volume or block device specified: {}".format(error_message)
        super(MainInvalidVolumeSpecificationError, self).__init__(message, *args)


class MainDirectoryError(MainError):
    """An error occurred while trying to create or modify a directory."""
    def __init__(self, error_message, *args):
        message = "Failed to create or modify directory: {}".format(error_message)
        super(MainDirectoryError, self).__init__(message, *args)


class MainMissingRequiredArgument(MainError):
    """The subcommand was missing a required, complementary argument."""
    def __init__(self, error_message, *args):
        message = "Missing argument: {}".format(error_message)
        super(MainMissingRequiredArgument, self).__init__(message, *args)


class MainVersionCheckTimeout(MainError):
    """A timeout occurred trying to connect to the S3 VERSION endpoint."""
    def __init__(self):
        message = "Connection timed out trying to obtain the latest version information."
        super(MainVersionCheckTimeout, self).__init__(message)


class MainUploadMissingSNISupport(MainError):
    """Built-in ssl module does not support SNI which is necessary for uploading to function."""
    def __init__(self):
        message = "Python built-in ssl module is missing Server Name Indication (SNI) support. " \
                  "Uploading will not function properly without support for SNI. " \
                  "Upgrade Python to 2.7.9+ / 3.2+ or retry with the binary build of ec2rl."
        super(MainUploadMissingSNISupport, self).__init__(message)


class MainSoftwareCheckPackageParsingFailure(MainError):
    """Failed to parse the package value into the name and URL."""
    def __init__(self, package_string, modules):
        message = "Failed to parse package string: '{}'. Malformed string present in the following modules: {}".format(
            package_string, modules)
        super(MainSoftwareCheckPackageParsingFailure, self).__init__(message)
