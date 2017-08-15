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
Module module.

Functions:
    module_constructor: the YAML constructor for a Module object
    get_module: helper that loads a Module object from the YAML file

Classes:
    Module: representation of an individual test module

Exceptions:
    ModuleError: base exception class for this module
    ModuleUnknownPlacementError: raised when an unsupported placement value is encountered
    ModulePathError: raised when an error occurs accessing the configuration file
    ModuleConstraintKeyError: raised when a Module is missing a required Constraint key
    ModuleRunFailureError: raised when a module is executed, but does not exit normally, indicating a run failure
    ModuleConstraintParseError: raised when the module is missing a required attribute value or the file failed to parse
    ModuleUnsupportedLanguageError: raised when an unsupported language value is encountered
"""

import os
import re
import subprocess
import sys
import tempfile

import yaml
import yaml.scanner

from ec2rlcore.logutil import LogUtil
import ec2rlcore.constraint

try:
    from yaml import CLoader as Loader
except ImportError:  # pragma: no cover
    from yaml import Loader


class Module(object):
    """
    Runnable class that represents a module and all its properties.

    Attributes:
        path (str): the full path to the module file
        placement (str): the stage where the module is to be run
        whyskipping (str): message stating why the module is being skipped
        applicable (bool): whether the module is applicable to the given system/OS configuration
        constraint (Constraint): represents the module's required arguments and system/OS configuration
        helptext (str): message providing usage information
        title (str): a short module summary
        name (str): the name of the module which is based on the filename
        processoutput (str): the output returns from subprocess.check_output()
        run_status (str): the run status of the module
        run_summary (str): the summary of the run of the module plus a short message relevant to the status
        logger (Logger): the logger object used to capture the different levels of logging message

    Methods:
        list: return the description message
        help: return the help message
        __call__: execture the module by means of the subprocess module
    """

    required_module_constraints = ["domain", "sudo", "required", "perfimpact", "software", "optional", "class",
                                   "parallelexclusive", "distro", "requires_ec2"]
    temp_path = ""

    placement_dir_mapping = {"run": "mod.d", "postdiagnostic": "post.d", "prediagnostic": "pre.d"}

    def __init__(self, name=None, version=None, title=None, helptext=None, placement=None,
                 package=None, language=None, content=None, path=None, constraint=None):
        """
        Perform initial configuration of the object. finish_init() needs to be called afterwards due the limitations of
        loading objects from YAML documents.

        Parameters:
            name (str): the name of the module
            version (str): the version string of the module
            title (str): the short title/help message for the module
            helptext (str): the full help message for the module
            placement (str): the placement of the module (at which stage it is to run)
            package (dict): the packages for required software
            language(str): the langugage the content is written in (will determine how the content is executed)
            content (str): the code for the module
            path (str): the full path to the module file
            constraint (ec2rlcore.constraint.Constraint): the Constraint object for this module
        """
        if not placement:
            raise ModuleConstraintParseError(
                "Module('{}'): must have a placement value in the configuration file!)".format(name))

        if placement not in self.placement_dir_mapping.keys():
            raise ModuleUnknownPlacementError(name, placement)

        # Verify all the required attributes have values
        if not name:
            raise ModuleConstraintParseError(
                "Module('{}'): must have a name value in the configuration file!)".format(path))
        if not version:
            raise ModuleConstraintParseError(
                "Module('{}'): must have a version value in the configuration file!)".format(name))
        if not title:
            raise ModuleConstraintParseError(
                "Module('{}'): must have a title value in the configuration file!)".format(name))
        if not helptext:
            raise ModuleConstraintParseError(
                "Module('{}'): must have a helptext value in the configuration file!)".format(name))
        if not package:
            raise ModuleConstraintParseError(
                "Module('{}'): must have a package value in the configuration file!)".format(name))
        if not language:
            raise ModuleConstraintParseError(
                "Module('{}'): must have a language value in the configuration file!)".format(name))
        if language not in ("bash", "python", "binary"):
            raise ModuleUnsupportedLanguageError(name, language)
        if not content:
            raise ModuleConstraintParseError(
                "Module('{}'): must have a content value in the configuration file!)".format(name))

        self.logger = LogUtil.get_root_logger()
        self.logger.debug("module.Module.__init__()")
        self.path = path
        self.name = name
        self.version = version
        self.title = title
        self.placement = placement
        self.package = package
        self.language = language
        self.content = content
        self.constraint = constraint

        self.whyskipping = ""
        self.processoutput = ""
        self.run_status = ""
        self.run_summary = ""
        self.run_status_details = list()

        # Start with the assumption that the module is applicable to the host under analysis
        self.applicable = True

        # Verify all required constraint metadata keys are present.
        for required_constraint in Module.required_module_constraints:
            if required_constraint not in self.constraint.without_keys([]):
                ec2rlcore.dual_log("Module parsing error: '{}' missing required constraint '{}'.".format(
                    os.path.basename(self.path), required_constraint))
                raise ModuleConstraintKeyError(os.path.basename(self.path), required_constraint)

        self.helptext = os.linesep.join((helptext, "Requires sudo: {}".format(self.constraint["sudo"][0])))

        return

    @property
    def list(self):
        """
        Return the formatted description line.

        Returns:
            (str): the formatted list message
        """
        self.logger.debug("module.Module.list()")
        # Print these values in using fixed widths with two space padding
        return "{:>1.1}{:>1.1}{:20.18}{:10.8}{:13.11}{:77.75}".format(
            "*" if self.constraint["sudo"][0] == "True" else "",
            "+" if self.constraint["perfimpact"][0] == "True"
            else "",
            self.name,
            ",".join(module_class
                     for module_class in self.constraint["class"]),
            ",".join(module_domain for module_domain in self.constraint["domain"]),
            self.title)

    @property
    def help(self):
        """
        Return the formatted help message.

        Returns:
            (str): the formatted help message
        """
        self.logger.debug("module.Module.help()")
        return os.linesep.join(["{}:".format(self.name),
                                self.helptext])

    def run(self, options=None):
        """
        Run the BASH module using the subprocess module and check that it successfully ran.

        Parameters:
             options: parsed command line argument:value pairs

        Returns:
            (str): output from module run subprocess.check_output
        """
        self.logger.debug("module.Module.run()")
        # Due to the use of temporary files for module execution, it is necessary to provide a way for a module
        # to know the originating file.
        os.environ["EC2RL_MODULE_PATH"] = self.path

        # limit the environment-variables inherited by the module execution
        envlist = {}
        for x in ("PATH",
                  "EC2RL_WORKDIR",
                  "EC2RL_RUNDIR",
                  "EC2RL_LOGDIR",
                  "EC2RL_GATHEREDDIR",
                  "EC2RL_DISTRO",
                  "EC2RL_NET_DRIVER",
                  "EC2RL_VIRT_TYPE",
                  "EC2RL_SUDO",
                  "EC2RL_PERFIMPACT",
                  "EC2RL_CALLPATH"):
            envlist[x] = os.environ[x]

        # Load the global values
        if options and options.global_args:
            for option, optionvalue in options.global_args.items():
                # subprocess requires all values be strings so attempt to cast any non-str values to str
                if type(optionvalue) != str:
                    optionvalue = str(optionvalue)
                envlist[option] = optionvalue

        # Load any module-specific values
        # Overwrite the values from global_args since they're less specific
        if options and options.per_module_args:
            self.logger.debug("Found options.per_module_args")
            if self.name in options.per_module_args:
                self.logger.debug("..Found {} in options.per_module_args".format(self.name))
                for option in options.per_module_args[self.name]:
                    optionvalue = options.per_module_args[self.name][option]
                    self.logger.debug("....Found option:value option {}:{}".format(option, optionvalue))
                    # subprocess requries all values be strings so attempt to cast any non-str values to str
                    if type(optionvalue) != str:
                        optionvalue = str(optionvalue)
                    envlist[option] = optionvalue

        if self.language == "binary":
            command = [os.sep.join((envlist["EC2RL_CALLPATH"],
                                    "bin",
                                    self.placement_dir_mapping[self.placement],
                                    self.name))]
        else:
            # Create a temporary file, write the value of the content attribute, and call the interpreter that matches
            # the language attribute.
            module_file = tempfile.NamedTemporaryFile()
            try:
                module_file.write(bytes(self.content, "utf8"))
            # Accommodate Python2 where bytes() takes a single arg
            except TypeError:
                module_file.write(bytes(self.content))

            module_file.flush()

            if self.language == "bash":
                command = ["/bin/bash", module_file.name]
            elif self.language == "python":
                command = [sys.executable, module_file.name]
            else:
                module_file.close()
                raise ModuleUnsupportedLanguageError(self.name, self.language)

        self.logger.info("command = {}".format(command))

        try:
            # subprocess.check_output will give output of command to STDOUT by default.
            # we can capture it into a variable, or immediately pass to a logging function/class (preferred)
            # If it bombs out, the stdout and return code are properties
            # within the subprocess.CalledProcessError that's raised.
            # See: https://docs.python.org/2/library/subprocess.html
            self.processoutput = subprocess.check_output(command, stderr=subprocess.STDOUT,
                                                         env=envlist).decode("utf-8")
            self._parse_output(self.processoutput)
            return self.processoutput
        except subprocess.CalledProcessError as processError:
            # type = bytes in Python3
            if isinstance(processError.output, bytes):
                self.processoutput = processError.output.decode("utf-8")
            # type = str in Python2
            else:
                self.processoutput = processError.output
            error_message = "Module execution failed: {}:{}, returned {}".format(self.placement, self.name,
                                                                                 processError.returncode)
            self.logger.debug(error_message)
            self.logger.debug(processError.cmd)
            self.logger.debug(processError.output)
            raise ModuleRunFailureError(error_message)
        finally:
            if "module_file" in vars():
                # noinspection PyUnboundLocalVariable
                module_file.close()

    def _parse_output(self, output):
        """
        Parse module process output to find status messages and notes
        Sets run_status, run_summary, and run_status_details

        Parameters:
            output: module output to parse

        Returns:
            bool: True if a status message was found
        """
        matched = False
        line_number = 0
        lines = output.strip().split("\n")
        for line in lines:
            line_number += 1
            line = line.rstrip()
            # import pdb; pdb.set_trace()
            if re.match(re.compile(r"\[SUCCESS\]"), line) and self.run_status != "WARN":
                self.run_status = "SUCCESS"
                self.run_summary = line
                self.run_status_details = self._parse_output_status_details(lines[line_number:])
                matched = True
            elif re.match(re.compile(r"\[FAILURE\]"), line):
                self.run_status = "FAILURE"
                self.run_summary = line
                self.run_status_details = self._parse_output_status_details(lines[line_number:])
                matched = True
                break
            elif re.match(re.compile(r"\[WARN\]"), line):
                self.run_status = "WARN"
                self.run_summary = line
                self.run_status_details = self._parse_output_status_details(lines[line_number:])
                matched = True
        if not matched:
            self.run_status = "UNKNOWN"
            self.run_summary = "[UNKNOWN] log missing SUCCESS, FAILURE, or WARN message."

        return matched

    @staticmethod
    def _parse_output_status_details(lines):
        """
        Parse a list of module output lines to locate detail lines.
        Stops searching after first non-matching line.

        Parameters:
             lines (list): module output to parse

        Returns:
            list(str): list of lines designated as details
        """
        details = list()
        detail_indicator = re.compile("^--")
        for line in lines:
            line = line.rstrip()
            if re.match(detail_indicator, line):
                details.append(line)
            else:
                break
        return details


class ModuleError(Exception):
    """Base class for exceptions in this module."""
    pass


class ModuleUnknownPlacementError(ModuleError):
    """An unsupported placement value was encountered."""
    def __init__(self, path, placement):
        message = "Unknown Placement '{}' defined for module '{}'.".format(placement, path)
        super(ModuleUnknownPlacementError, self).__init__(message)


class ModulePathError(ModuleError):
    """An error accessing the file occurred."""
    def __init__(self, path, *args):
        message = "Invalid Module Path defined: " + path
        super(ModulePathError, self).__init__(message, *args)


class ModuleConstraintKeyError(ModuleError):
    """A required Module Constraint key is missing."""
    def __init__(self, module_name, constraint_name, *args):
        message = "Module file {} missing constraint key: {}".format(module_name, constraint_name)
        super(ModuleConstraintKeyError, self).__init__(message, *args)


class ModuleRunFailureError(ModuleError):
    """The module's execution did not exit normally."""
    def __init__(self, message, *args):
        super(ModuleRunFailureError, self).__init__(message, *args)


class ModuleConstraintParseError(ModuleError):
    """The module is missing a required attribute value."""
    def __init__(self, message, *args):
        super(ModuleConstraintParseError, self).__init__(message, *args)


class ModuleUnsupportedLanguageError(ModuleError):
    """An unsupported language value was encountered."""
    def __init__(self, module_name, language_name, *args):
        message = "Module file {} contains an unsupported language: {}".format(module_name, language_name)
        super(ModuleUnsupportedLanguageError, self).__init__(message, *args)


def module_constructor(loader, node):
    """
    This is the yaml constructor for a Module object. First, the object mapping is loaded from the yaml module file.
    Next, the "constraint" key value is replaced with with a Constraint object created from the value loaded from the
    yaml module file.
    Then the module's filename path is added to the mapping.
    The last mapping edit is to remove the trailing newlines from the string values in the mapping. This is done to
    keep the values consistent with the pre-yaml values. In doing so, the displayed text is consistent and tests do not
    need to be updated.
    Lastly, __init__ is called to finish creating the Module.
    """
    new_module = Module.__new__(Module)
    yield new_module
    values = loader.construct_mapping(node, deep=True)
    values["constraint"] = ec2rlcore.constraint.Constraint(values["constraint"])
    values["path"] = Module.temp_path
    # Strip trailing newlines from string values where yaml added them (e.g. title, helptext)
    for key in values.keys():
        if isinstance(values[key], str):
            values[key] = values[key].rstrip()
    new_module.__init__(**values)


def get_module(filename_with_path):
    """
    Given a filename with an absolute path, load the contents, instantiate a Module, and set the Module's path
    attribute.

    Parameters:
        filename_with_path (str): the YAML filename with an absolute path
    """
    try:
        with open(filename_with_path) as config_file:
            Module.temp_path = filename_with_path
            this_module = yaml.load(config_file, Loader=Loader)
            Module.temp_path = ""
            return this_module
    except IOError:
        raise ModulePathError(filename_with_path)
    except yaml.scanner.ScannerError:
        raise ModuleConstraintParseError("Parsing of module {} failed. This is likely caused by a typo in the file."
                                         "".format(filename_with_path))
# Add the YAML Module constructor so that YAML knows to use it in situations where the tag matches.
yaml.add_constructor("!ec2rlcore.module.Module", module_constructor, Loader=Loader)


class SkipReason:
    NOT_AN_EC2_INSTANCE = "NOT_AN_EC2_INSTANCE"
    NOT_APPLICABLE_TO_DISTRO = "NOT_APPLICABLE_TO_DISTRO"
    PERFORMANCE_IMPACT = "PERFORMANCE_IMPACT"
    REQUIRES_SUDO = "REQUIRES_SUDO"
    NOT_SELECTED = "NOT_SELECTED"
    MISSING_SOFTWARE = "MISSING_SOFTWARE"
    MISSING_ARGUMENT = "MISSING_ARGUMENT"
