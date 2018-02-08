# Copyright 2016-2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
Unit tests for the selinuxpermissive module
"""
import os
import sys
import unittest

import mock

import moduletests.src.selinuxpermissive

try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib


class Testselinuxpermissive(unittest.TestCase):
    config_file_path = "/etc/selinux/config"

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("moduletests.src.selinuxpermissive.os.path.isfile", return_value=False)
    def test_detect_no_selinux(self, isfile_mock):
        self.assertFalse(moduletests.src.selinuxpermissive.detect(self.config_file_path))
        self.assertTrue(isfile_mock.called)

    @mock.patch("moduletests.src.selinuxpermissive.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.open", mock.mock_open(read_data="SELINUX=enforcing"))
    def test_detect_problem(self, isfile_mock):
        self.assertTrue(moduletests.src.selinuxpermissive.detect(self.config_file_path))
        self.assertTrue(isfile_mock.called)

    @mock.patch("moduletests.src.selinuxpermissive.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.open", mock.mock_open(read_data="SELINUX=permissive"))
    def test_detect_noproblem(self, isfile_mock):
        self.assertFalse(moduletests.src.selinuxpermissive.detect(self.config_file_path))
        self.assertTrue(isfile_mock.called)

    @mock.patch("moduletests.src.selinuxpermissive.open", mock.mock_open(read_data="SELINUX=enforcing"))
    def test_fix_success(self):
        self.assertTrue(moduletests.src.selinuxpermissive.fix(self.config_file_path))

    @mock.patch("moduletests.src.selinuxpermissive.open", side_effect=IOError)
    def test_fix_exception(self, open_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(IOError, moduletests.src.selinuxpermissive.fix, self.config_file_path)
        self.assertEqual(self.output.getvalue(), "[WARN] Unable to replace contents of /etc/selinux/config\n")
        self.assertTrue(open_mock.called)

    @mock.patch("moduletests.src.selinuxpermissive.get_config_dict")
    @mock.patch("moduletests.src.selinuxpermissive.detect", side_effect=(True, False))
    @mock.patch("moduletests.src.selinuxpermissive.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.backup", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.fix", return_value=True)
    def test_run_success_fixed(self, fix_mock, backup_mock, isfile_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.selinuxpermissive.run())
        self.assertTrue("[SUCCESS] selinux set to permissive" in self.output.getvalue())
        self.assertTrue(fix_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.selinuxpermissive.get_config_dict", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.detect", return_value=False)
    def test_run_success(self, detect_mock, config_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.selinuxpermissive.run())
        self.assertTrue("[SUCCESS] selinux is not set to enforcing" in self.output.getvalue())
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.selinuxpermissive.get_config_dict")
    @mock.patch("moduletests.src.selinuxpermissive.detect", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.backup", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.fix", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.restore", return_value=True)
    def test_run_failure_isfile(self, 
                                restore_mock, 
                                fix_mock, 
                                backup_mock, 
                                isfile_mock, 
                                detect_mock, 
                                config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": {self.config_file_path: "/some/path"},
                                    "REMEDIATE": True,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.selinuxpermissive.run())
        self.assertTrue("[FAILURE] failed to set selinux set to permissive" in self.output.getvalue())
        self.assertTrue(restore_mock.called)
        self.assertTrue(fix_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.selinuxpermissive.get_config_dict")
    @mock.patch("moduletests.src.selinuxpermissive.detect", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.os.path.isfile", return_value=False)
    @mock.patch("moduletests.src.selinuxpermissive.fix", return_value=True)
    def test_run_failure(self, fix_mock, isfile_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.selinuxpermissive.run())
        self.assertTrue("[FAILURE] failed to set selinux set to permissive" in self.output.getvalue())
        self.assertTrue(fix_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.selinuxpermissive.get_config_dict")
    @mock.patch("moduletests.src.selinuxpermissive.detect", side_effect=IOError)
    @mock.patch("moduletests.src.selinuxpermissive.restore", return_value=True)
    def test_run_failure_exception(self, restore_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": {self.config_file_path: "/some/path"},
                                    "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.selinuxpermissive.run())
        self.assertTrue(self.output.getvalue().endswith("Review the logs to determine the cause of the issue.\n"))
        self.assertTrue(restore_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.selinuxpermissive.get_config_dict", side_effect=IOError)
    def test_run_failure_config_exception(self, config_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.selinuxpermissive.run())
        self.assertTrue(self.output.getvalue().endswith("Review the logs to determine the cause of the issue.\n"))
        self.assertTrue(config_mock.called)
