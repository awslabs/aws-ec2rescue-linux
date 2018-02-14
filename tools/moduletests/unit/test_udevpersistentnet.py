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
Unit tests for the udevpersistentnet module
"""
import os
import sys
import unittest

import mock

import moduletests.src.udevpersistentnet

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


class Testudevpersistentnet(unittest.TestCase):
    rules_file = "/etc/udev/rules.d/70-persistent-net.rules"

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("moduletests.src.udevpersistentnet.os.path.isfile", return_value=False)
    def test_detect_noproblem(self, isfile_mock):
        self.assertFalse(moduletests.src.udevpersistentnet.detect(self.rules_file))
        self.assertTrue(isfile_mock.called)

    @mock.patch("moduletests.src.udevpersistentnet.os.path.isfile", return_value=True)
    def test_detect_problem(self, isfile_mock):
        self.assertTrue(moduletests.src.udevpersistentnet.detect(self.rules_file))
        self.assertTrue(isfile_mock.called)

    @mock.patch("os.chown", return_value=True)
    @mock.patch("os.chmod", return_value=True)
    @mock.patch("shutil.copy2", return_value=True)
    def test_fix_success(self, copy2_mock, os_chmod_mock, os_chown_mock):
        # A comment, a valid line, and a line consisting of whitespace
        line = "# a comment\n" \
               "SUBSYSTEM==\"net\", " \
               "ACTION==\"add\", " \
               "DRIVERS==\"?*\", " \
               "ATTR{address}==\"0e:1e:4f:fd:a1:2c\", " \
               "NAME=\"eth0\"\n" \
               "\t\n"
        open_mock = mock.mock_open(read_data=line)
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")

        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func

        # noinspection PyUnresolvedReferences
        with mock.patch.object(moduletests.src.udevpersistentnet.tempfile, "NamedTemporaryFile") as temp_file_mock:
            with mock.patch("moduletests.src.udevpersistentnet.open", open_mock):
                with contextlib.redirect_stdout(StringIO()):
                    self.assertTrue(moduletests.src.udevpersistentnet.fix(self.rules_file))
                self.assertTrue(temp_file_mock.called)
                self.assertEqual(str(temp_file_mock.mock_calls),
                                 '[call(mode=\'wt\'),\n call().__enter__(),\n '
                                 'call().__enter__().write(\'# a comment\\n\'),\n '
                                 'call().__enter__().write(\'# SUBSYSTEM=="net", '
                                 'ACTION=="add", DRIVERS=="?*", '
                                 'ATTR{address}=="0e:1e:4f:fd:a1:2c", '
                                 'NAME="eth0" # commented out by ec2rl\\n\'),\n '
                                 'call().__enter__().write(\'\\t\\n\'),\n '
                                 'call().__enter__().flush(),\n '
                                 'call().__exit__(None, None, None)]')
                self.assertTrue(open_mock.called)
                self.assertTrue(copy2_mock.called)
                self.assertTrue(os_chmod_mock.called)
                self.assertTrue(os_chown_mock.called)

    @mock.patch("moduletests.src.udevpersistentnet.get_config_dict")
    @mock.patch("moduletests.src.udevpersistentnet.detect", return_value=True)
    @mock.patch("moduletests.src.udevpersistentnet.backup", return_value=True)
    @mock.patch("moduletests.src.udevpersistentnet.fix", return_value=True)
    def test_run_success(self, fix_mock, detect_mock, backup_mock, get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": dict(),
                                             "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.udevpersistentnet.run())
        self.assertTrue(self.output.getvalue().endswith("/docs/modules/udevpersistentnet.md for further details\n"))
        self.assertTrue(detect_mock.called)
        self.assertTrue(fix_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.udevpersistentnet.get_config_dict")
    @mock.patch("moduletests.src.udevpersistentnet.detect", return_value=True)
    @mock.patch("moduletests.src.udevpersistentnet.backup", return_value=True)
    @mock.patch("moduletests.src.udevpersistentnet.fix", return_value=False)
    def test_run_success_failure(self, fix_mock, backup_mock, detect_mock, get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": dict(),
                                             "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.udevpersistentnet.run())
        self.assertTrue("[FAILURE] failed to comment out the lines in /etc/udev/rules.d/70-persistent-net.rules"
                        in self.output.getvalue())
        self.assertTrue(fix_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.udevpersistentnet.get_config_dict")
    @mock.patch("moduletests.src.udevpersistentnet.detect", return_value=False)
    def test_run_no_rule_file(self, detect_mock, get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": dict(),
                                             "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.udevpersistentnet.run())
        self.assertTrue("[SUCCESS] /etc/udev/rules.d/70-persistent-net.rules not present."
                        in self.output.getvalue())
        self.assertTrue(detect_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.udevpersistentnet.get_config_dict")
    @mock.patch("moduletests.src.udevpersistentnet.detect", return_value=True)
    @mock.patch("moduletests.src.udevpersistentnet.backup", return_value=True)
    @mock.patch("moduletests.src.udevpersistentnet.fix", side_effect=IOError())
    @mock.patch("moduletests.src.udevpersistentnet.restore", return_value=True)
    def test_run_failure(self, restore_mock, fix_mock, backup_mock, detect_mock, get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": {self.rules_file: "/some/path"},
                                             "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.udevpersistentnet.run())
        self.assertTrue(self.output.getvalue().endswith("Review the logs to determine the cause of the issue.\n"))
        self.assertTrue(restore_mock.called)
        self.assertTrue(fix_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.udevpersistentnet.get_config_dict", side_effect=Exception)
    def test_run_config_exception(self, get_config_dict_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.udevpersistentnet.run())
        self.assertTrue(self.output.getvalue().endswith("Review the logs to determine the cause of the issue.\n"))
        self.assertTrue(get_config_dict_mock.called)
