# Copyright 2016-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/


# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""
Logging utilities to provide default configuration and module specific logging

Functions:
    None

Classes:
    LogUtil: logging-like class for managing message logging to files

Exceptions:
    None
"""

import logging
import os

try:
    # Python 3.x
    from builtin import FileExistsError
except ImportError:
    # Python 2.7
    FileExistsError = OSError


class LogUtil(object):
    """
    Logging utilities to configure root and module specific loggers

    Methods:
        get_root_logger: returns the root logger for general use.
        set_main_log_handler: add a file handler for the main log file.
        set_debug_log_handler: add a file handler for the debug log file.
        set_console_log_handler: enables and sets the log level of console output.
        get_direct_console_logger: returns the named 'console' logger
        set_direct_console_logger: sets the named 'console' logger
        disable_console_output: disable the logger's output to the local console.
        get_module_logger: returns a module specific Logger
        create_module_logger: sets initial configuration of a module specific logger
    """
    _format = "%(asctime)s %(filename)-10s %(levelname)-8s: %(message)s"
    _handlers = dict()
    _module_loggers = list()

    @staticmethod
    def get_root_logger():
        return logging.getLogger("ec2rl")

    @classmethod
    def set_main_log_handler(cls, logfile):
        """
        Set main log file location.

        Parameters:
            logfile (str) : file path

        Returns:
            True (bool)
        """
        logger = cls.get_root_logger()
        logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler(logfile)
        fh.setFormatter(logging.Formatter(cls._format, "%Y-%m-%dT%T%Z"))
        fh.setLevel(logging.INFO)

        if "main" in cls._handlers:
            main_handler = cls._handlers["main"]
            main_handler.close()
            logger.removeHandler(main_handler)
            cls._handlers.pop("main")

        cls._handlers["main"] = fh
        logger.addHandler(fh)
        return True

    @classmethod
    def set_debug_log_handler(cls, logfile):
        """
        Set debug log file location.

        Parameters:
            logfile (str) : file path

        Returns:
            True (bool)
        """
        logger = cls.get_root_logger()
        logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler(logfile)
        fh.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%dT%T%Z"))
        fh.setLevel(logging.DEBUG)

        if "debug" in cls._handlers:
            logger.removeHandler(cls._handlers["debug"])
            debug_handler = cls._handlers["debug"]
            debug_handler.close()
            logger.removeHandler(debug_handler)
            cls._handlers.pop("debug")

        cls._handlers["debug"] = fh
        logger.addHandler(fh)
        return True

    @classmethod
    def set_console_log_handler(cls, loglevel=logging.DEBUG):
        """
        Enable local console output of logger.

        Parameters:
            loglevel (int): numeric value of the logging level (e.g. DEBUG == 10)

        Returns:
            True (bool)
        """
        logger = cls.get_root_logger()  # .getChild("console")

        if loglevel > 50 and "console" in cls._handlers:
            console_handler = cls._handlers["console"]
            console_handler.close()
            logger.removeHandler(console_handler)
            cls._handlers.pop("console")

        ch = logging.StreamHandler()
        ch.setLevel(loglevel)

        if "console" in cls._handlers:
            logger.removeHandler(cls._handlers["console"])

        cls._handlers["console"] = ch
        logger.addHandler(ch)
        return True

    @classmethod
    def get_direct_console_logger(cls):
        """Return the root logger's child named 'console'."""
        return cls.get_root_logger().getChild("console")

    @classmethod
    def set_direct_console_logger(cls, loglevel=logging.INFO):
        """
        Configure and add the handler for the direct console logger.

        Parameters:
            loglevel (int): numeric value of the logging level (e.g. DEBUG == 10)

        Returns:
            logger (Logger): the root logger's child named 'console'
        """
        logger = cls.get_root_logger().getChild("console")
        logger.setLevel(logging.DEBUG)
        consolehandler = logging.StreamHandler()
        consolehandler.setLevel(loglevel)
        logger.addHandler(consolehandler)
        logger.propagate = True
        return logger

    @classmethod
    def disable_console_output(cls):
        """
        Disable local console output of logger.

        Returns:
            True (bool)
        """
        cls.set_console_log_handler(100)
        return True

    @classmethod
    def get_module_logger(cls, mod, logdir):
        """
        Returns a logging.Logger specific to the given module.
        If the logger has not yet been configured, it will be created with default options
        by LogUtil.create_module_logger()

        Parameters:
            mod (Module): module to return a logger for
            logdir (str): the log directory path

        Returns:
            (logger): logging.Logger specific to the given ec2rlcore.module
        """
        if "{}:{}".format(mod.placement, mod.name) not in cls._module_loggers:
            cls.create_module_logger(mod, logdir)

        return logging.getLogger("ec2rl").getChild("module").getChild(mod.placement).getChild(mod.name)

    @classmethod
    def create_module_logger(cls, mod, logdir):
        """
        Performs initial setup of a module-level logger.
        The logging.Logger can be retrieved with get_module_logger, so storing the
        return value of this function is not necessary

        Parameters:
            mod (Module): ec2rlcore.module to create a logger for.
            logdir (str): the log directory path

        Returns:
            module_logger (Logger): The created logging.Logger for the module.
        """

        module_log_dir = os.sep.join((logdir, mod.placement))

        # Create the directory, if needed.
        try:
            os.makedirs(module_log_dir)
        except FileExistsError:
            pass
        file_name_with_path = os.sep.join((module_log_dir, mod.name + ".log"))
        module_fh = logging.FileHandler(file_name_with_path)
        module_fh.setFormatter("")
        module_logger = logging.getLogger("ec2rl").getChild("module").getChild(mod.placement).getChild(mod.name)
        module_logger.addHandler(module_fh)
        module_logger.propagate = False

        if "{}:{}".format(mod.placement, mod.name) not in cls._module_loggers:
            cls._module_loggers.append("{}:{}".format(mod.placement, mod.name))
        return module_logger

    @classmethod
    def dual_log_info(cls, message):
        """Log the message to the root logger at the INFO level and also print it to stdout."""
        cls.get_root_logger().info(message)
        print(message)
