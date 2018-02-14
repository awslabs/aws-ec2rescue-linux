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
Unit tests for the arpignore module
"""
import os
import subprocess
import sys
import unittest

import mock

import moduletests.src.arpignore

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

# builtins was named __builtin__ in Python 2 so accommodate the change for the purposes of mocking the open call
if sys.version_info >= (3,):
    builtins_name = "builtins"
else:
    builtins_name = "__builtin__"


class Testarpignore(unittest.TestCase):
    config_file_path = "/etc/sysctl.d/55-arp-ignore.conf"

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("subprocess.check_output")
    def test_detect_noproblem(self, check_output_mock):
        """Test that no problem is detected with expected-good output."""
        check_output_mock.return_value = "arp_ignore = 0"
        self.assertFalse(moduletests.src.arpignore.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output")
    def test_detect_problem(self, check_output_mock):
        """Test that the problem is detected with expected-bad output."""
        check_output_mock.return_value = "arp_ignore = 1"
        self.assertTrue(moduletests.src.arpignore.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=["net.ipv4.conf.all.arp_ignore = 1",
                                                        subprocess.CalledProcessError(1, "test")])
    def test_fix_sysctlfail(self, check_output_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(subprocess.CalledProcessError, moduletests.src.arpignore.fix, self.config_file_path)
        self.assertTrue(check_output_mock.called)
        self.assertTrue(self.output.getvalue().endswith(
            "[UNFIXED] net.ipv4.conf.all.arp_ignore=0 failed for running system\n"))

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.arpignore.os.path.exists", side_effect=[False])
    @mock.patch("moduletests.src.arpignore.open", side_effect=IOError)
    def test_fix_write_new_fail(self, open_mock, exists_mock, check_output_mock):
        check_output_mock.return_value = "net.ipv4.conf.lo.arp_announce = 0\nnet.ipv4.conf.all.arp_ignore = 1"
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(IOError, moduletests.src.arpignore.fix, self.config_file_path)
        self.assertTrue(open_mock.called)
        self.assertTrue(exists_mock.called)
        self.assertTrue(check_output_mock.called)
        self.assertTrue(self.output.getvalue().endswith(
            "[UNFIXED] Unable to open /etc/sysctl.d/55-arp-ignore.conf and write to it.\n"))

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.arpignore.os.path.exists", side_effect=[False])
    @mock.patch("moduletests.src.arpignore.open", mock.mock_open())
    def test_fix_write_new_success(self, exists_mock, check_output_mock):
        check_output_mock.return_value = "net.ipv4.conf.lo.arp_announce = 0\nnet.ipv4.conf.all.arp_ignore = 1"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpignore.fix(self.config_file_path))
        self.assertTrue(self.output.getvalue().endswith("[FIXED] /etc/sysctl.d/55-arp-ignore.conf written.\n"))
        self.assertTrue(exists_mock.called)
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.arpignore.os.path.exists", side_effect=[True])
    def test_fix_success(self, exists_mock, check_output_mock):
        check_output_mock.return_value = "net.ipv4.conf.all.arp_ignore = 1\nsome_other = 0"
        open_mock = mock.mock_open(read_data="#comment\n"
                                             "net.ipv4.conf.all.arp_ignore = 1\n"
                                             "net.ipv4.conf.lo.arp_ignore = 0\n"
                                             "garbage\n")

        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)
        def iter_func(self):
            return iter(self.readline, "")

        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("moduletests.src.arpignore.open", open_mock):
            with contextlib.redirect_stdout(self.output):
                self.assertTrue(moduletests.src.arpignore.fix(self.config_file_path))
        self.assertTrue(self.output.getvalue().endswith("[FIXED] /etc/sysctl.d/55-arp-ignore.conf written.\n"))
        self.assertEqual(str(open_mock.mock_calls), "[call('/etc/sysctl.d/55-arp-ignore.conf', 'r'),\n"
                                                    " call().__enter__(),\n call().readlines(),\n"
                                                    " call().__exit__(None, None, None),\n"
                                                    " call('/etc/sysctl.d/55-arp-ignore.conf', 'w'),\n"
                                                    " call().__enter__(),\n"
                                                    " call().write('#comment\\nnet.ipv4.conf.lo.arp_ignore = 0'),\n"
                                                    " call().write('\\n'),\n"
                                                    " call().write('net.ipv4.conf.all.arp_ignore = 0'),\n"
                                                    " call().write('\\n'),\n"
                                                    " call().__exit__(None, None, None)]")
        self.assertTrue(exists_mock.called)
        self.assertTrue(check_output_mock.called)

    @mock.patch("moduletests.src.arpignore.get_config_dict", return_value=dict())
    @mock.patch("moduletests.src.arpignore.detect", return_value=False)
    def test_run_success(self, detect_mock, config_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpignore.run())
        self.assertEqual(self.output.getvalue(), "Determining if any interfaces are set to ignore arp requests\n"
                                                 "[SUCCESS] arp ignore is disabled for all interfaces.\n")
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpignore.get_config_dict")
    @mock.patch("moduletests.src.arpignore.detect", return_value=True)
    def test_run_no_remediate(self, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": False,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.arpignore.run())
        self.assertTrue("[UNFIXED] Remediation impossible without sudo and --remediate.\n"
                        "-- Running as root/sudo: True\n"
                        "-- Required --remediate flag specified: False\n"
                        "[FAILURE] arp ignore is enabled for one or more interfaces. Please see the module log\n"
                        in self.output.getvalue())
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpignore.get_config_dict")
    @mock.patch("moduletests.src.arpignore.detect", return_value=True)
    @mock.patch("moduletests.src.arpignore.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.arpignore.backup", return_value=True)
    @mock.patch("moduletests.src.arpignore.fix", return_value=True)
    @mock.patch("moduletests.src.arpignore.restore", return_value=True)
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
            self.assertFalse(moduletests.src.arpignore.run())
        self.assertTrue("[FAILURE] arp ignore is enabled for one or more interfaces. "
                        "Please see the module log"
                        in self.output.getvalue())
        self.assertTrue(restore_mock.called)
        self.assertTrue(fix_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpignore.get_config_dict")
    @mock.patch("moduletests.src.arpignore.detect", return_value=True)
    @mock.patch("moduletests.src.arpignore.os.path.isfile", return_value=False)
    @mock.patch("moduletests.src.arpignore.fix", return_value=True)
    def test_run_failure(self, fix_mock, isfile_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.arpignore.run())
        self.assertTrue("[FAILURE] arp ignore is enabled for one or more interfaces. "
                        "Please see the module log"
                        in self.output.getvalue())
        self.assertTrue(fix_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpignore.get_config_dict")
    @mock.patch("moduletests.src.arpignore.detect", side_effect=(True, False))
    @mock.patch("moduletests.src.arpignore.os.path.isfile", return_value=False)
    @mock.patch("moduletests.src.arpignore.fix", return_value=True)
    def test_run_fix(self, fix_mock, isfile_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpignore.run())
        self.assertEqual(self.output.getvalue(), "Determining if any interfaces are set to ignore arp requests\n"
                                                 "[SUCCESS] arp ignore is disabled for all interfaces "
                                                 "after remediation.\n")
        self.assertTrue(fix_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpignore.get_config_dict")
    @mock.patch("moduletests.src.arpignore.detect", side_effect=Exception)
    @mock.patch("moduletests.src.arpignore.restore", return_value=True)
    def test_run_exception(self, restore_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": {self.config_file_path: "/some/path"},
                                    "REMEDIATE": True,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.arpignore.run())
        self.assertTrue(restore_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpignore.get_config_dict", side_effect=IOError)
    def test_run_failure_config_exception(self, config_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.arpignore.run())
        self.assertTrue(self.output.getvalue().endswith("Review the logs to determine the cause of the issue.\n"))
        self.assertTrue(config_mock.called)
