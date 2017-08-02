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

"""Unit tests for "logutil" module."""
import logging
import os
import sys
import unittest

import mock

import ec2rlcore.logutil
import ec2rlcore.module


def simple_return(*args, **kwargs):
    return True


class TestLogUtil(unittest.TestCase):
    """Testing class for "logutil" unit tests."""

    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    if os.path.isdir(_callp):
        callpath = _callp
    else:
        callpath = os.path.split(_callp)[0]

    log_path = module_path = os.path.join(callpath, "test/test.log")

    def setUp(self):
        """Default Options."""
        return

    def tearDown(self):
        """Clear the module loggers between tests."""
        ec2rlcore.logutil.LogUtil._module_loggers = list()

    def test_logutil_get_root_logger(self):
        """Test that get_root_logger returns a Logger type object."""
        logger = ec2rlcore.logutil.LogUtil.get_root_logger()
        self.assertIsInstance(logger, logging.Logger)

    def test_logutil_get_direct_console_logger(self):
        """Test that get_direct_console_logger returns a Logger type object."""
        logger = ec2rlcore.logutil.LogUtil.get_direct_console_logger()
        self.assertIsInstance(logger, logging.Logger)

    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("logging.FileHandler")
    def test_logutil_get_module_logger(self, logging_fh_mock, os_makedirs_mock):
        """Test that get_module_logger returns a Logger type object."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        module_path = os.path.join(self.callpath, "test/modules/mod.d/arpcache.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)

        logger = ec2rlcore.logutil.LogUtil.get_module_logger(module_obj, os.path.join(self.callpath, "test"))
        self.assertIsInstance(logger, logging.Logger)
        self.assertTrue(logging_fh_mock.called)
        self.assertTrue(os_makedirs_mock.called)

    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("logging.FileHandler")
    def test_logutil_get_module_logger_exists(self, logging_fh_mock, os_makedirs_mock):
        """Test that get_module_logger returns the existing logger object for a module."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        module_path = os.path.join(self.callpath, "test/modules/mod.d/arpcache.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)

        logger1 = ec2rlcore.logutil.LogUtil.get_module_logger(module_obj, os.path.join(self.callpath, "test"))
        logger2 = ec2rlcore.logutil.LogUtil.get_module_logger(module_obj, os.path.join(self.callpath, "test"))
        self.assertEqual(logger1, logger2)
        self.assertTrue(logging_fh_mock.called)
        self.assertTrue(os_makedirs_mock.called)

    @mock.patch("logging.FileHandler")
    def test_logutil_set_main_log_handler(self, logging_fh_mock):
        """Test that set_main_log_handler was able to set the file handler."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        self.assertTrue(ec2rlcore.logutil.LogUtil.set_main_log_handler(self.log_path))
        # Performing this the second time will result in set_main_log_handler() closing the existing "main" file handle
        # and removing that file handle prior to adding the new "main" file handle.
        self.assertTrue(ec2rlcore.logutil.LogUtil.set_main_log_handler(self.log_path))
        self.assertTrue(logging_fh_mock.called)

    @mock.patch("logging.FileHandler")
    def test_logutil_set_debug_log_handler(self, logging_fh_mock):
        """Test that set_debug_log_handler was able to set the file handler."""
        self.assertTrue(ec2rlcore.logutil.LogUtil.set_debug_log_handler(self.log_path))
        # Performing this the second time will result in set_debug_log_handler() closing the existing "debug" file
        # handle and removing that file handle prior to adding the new "debug" file handle.
        self.assertTrue(ec2rlcore.logutil.LogUtil.set_debug_log_handler(self.log_path))
        self.assertTrue(logging_fh_mock.called)

    def test_logutil_disable_console_output(self):
        """Test that disable_console_output was able to set the console file handler to None."""
        self.assertTrue(ec2rlcore.logutil.LogUtil.disable_console_output())

    def test_logutil_set_console_log_handler(self):
        """Test that set_console_log_handler was able to set the console log handler."""
        self.assertTrue(ec2rlcore.logutil.LogUtil.set_console_log_handler(loglevel=100))
        self.assertTrue(ec2rlcore.logutil.LogUtil.set_console_log_handler(loglevel=50))

    def test_logutil_set_direct_console_logger(self):
        """Test that set_direct_console_logger returns a Logger type object."""
        logger = ec2rlcore.logutil.LogUtil.set_direct_console_logger(loglevel=100)
        self.assertIsInstance(logger, logging.Logger)

    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("logging.FileHandler")
    def test_logutil_create_module_logger(self, logging_fh_mock, os_makedirs_mock):
        """Test that create_module_logger returns a Logger type object."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        module_path = os.path.join(self.callpath, "test/modules/mod.d/arptable.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)

        logger = ec2rlcore.logutil.LogUtil.create_module_logger(module_obj, os.path.join(self.callpath, "test"))
        self.assertIsInstance(logger, logging.Logger)
        self.assertTrue(logging_fh_mock.called)
        self.assertTrue(os_makedirs_mock.called)

    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("logging.FileHandler")
    def test_logutil_create_module_logger_exists(self, logging_fh_mock, os_makedirs_mock):
        """Test that create_module_logger does not add duplicates."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        module_path = os.path.join(self.callpath, "test/modules/mod.d/arptable.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)

        logger1 = ec2rlcore.logutil.LogUtil.create_module_logger(module_obj, os.path.join(self.callpath, "test"))
        logger2 = ec2rlcore.logutil.LogUtil.create_module_logger(module_obj, os.path.join(self.callpath, "test"))
        qty_found = 0
        for logger in ec2rlcore.logutil.LogUtil._module_loggers:
            if logger == "run:arptable":
                qty_found += 1

        self.assertEqual(logger1, logger2)
        self.assertEqual(qty_found, 1)
        self.assertTrue(logging_fh_mock.called)
        self.assertTrue(os_makedirs_mock.called)
