# Copyright 2016-2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
Unit tests for the tcprecycle module
"""
import subprocess
import sys
import unittest

import mock

import moduletests.src.tcprecycle

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


class Testtcprecycle(unittest.TestCase):
    config_file_path = "/etc/sysctl.d/55-tcp_rw_recycle.conf"

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("subprocess.check_output")
    def test_detect_notapplicable(self, check_output_mock):
        check_output_mock.return_value = "net.ipv4.tcp_syncookies = 1"
        self.assertFalse(moduletests.src.tcprecycle.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output")
    def test_detect_noproblem(self, check_output_mock):
        check_output_mock.return_value = "net.ipv4.tcp_tw_recycle = 0"
        self.assertFalse(moduletests.src.tcprecycle.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output")
    def test_detect_problem(self, check_output_mock):
        check_output_mock.return_value = "net.ipv4.tcp_tw_recycle = 1"
        self.assertTrue(moduletests.src.tcprecycle.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        "1", "test", "/etc/sysctl.d/55-tcp_rw_recycle.conf: no such file or directory"))
    def test_fix_cpe(self, check_output_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(subprocess.CalledProcessError, moduletests.src.tcprecycle.fix, self.config_file_path)
        self.assertTrue(self.output.getvalue().endswith(
            "[UNFIXED] sysctl -w net.ipv4.tcp_tw_recycle=0 failed for running system\n"))
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.tcprecycle.os.path.exists", side_effect=[False])
    @mock.patch("moduletests.src.tcprecycle.open", mock.mock_open(read_data="stuff"))
    def test_fix_exists_sudo_true(self, check_output_mock, exists_mock):
        check_output_mock.return_value = "True"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.tcprecycle.fix(self.config_file_path))
        self.assertTrue(self.output.getvalue().endswith(
            "[FIXED] net.ipv4.tcp_tw_recycle=0 for running system\n"
            "[FIXED] net.ipv4.tcp_tw_recycle=0 in /etc/sysctl.d/55-tcp_rw_recycle.conf\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(exists_mock.called)

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.tcprecycle.os.path.exists", side_effect=[True])
    @mock.patch("moduletests.src.tcprecycle.open", mock.mock_open(read_data="net.ipv4.tcp_tw_recycle = 0\n"
                                                                            "something else\n"))
    def test_fix_sudo_true(self, check_output_mock, exists_mock):
        check_output_mock.return_value = "True"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.tcprecycle.fix(self.config_file_path))
        self.assertTrue(self.output.getvalue().endswith(
            "[FIXED] net.ipv4.tcp_tw_recycle=0 for running system\n"
            "[FIXED] net.ipv4.tcp_tw_recycle=0 in /etc/sysctl.d/55-tcp_rw_recycle.conf\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(exists_mock.called)

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.tcprecycle.os.path.exists", side_effect=[True])
    @mock.patch("moduletests.src.tcprecycle.open", mock.mock_open(read_data="net.ipv4.tcp_tw_recycle = 0\n"
                                                                            "net.ipv4.tcp_tw_recycle = 0\n"))
    def test_fix_sudo_true_found_twice(self, check_output_mock, exists_mock):
        check_output_mock.return_value = "True"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.tcprecycle.fix(self.config_file_path))
        self.assertTrue(self.output.getvalue().endswith(
            "[FIXED] net.ipv4.tcp_tw_recycle=0 for running system\n"
            "[FIXED] net.ipv4.tcp_tw_recycle=0 in /etc/sysctl.d/55-tcp_rw_recycle.conf\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(exists_mock.called)

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.tcprecycle.os.path.exists", side_effect=[False])
    @mock.patch("moduletests.src.tcprecycle.open", side_effect=IOError)
    def test_fix_writefail(self, open_mock, exists_mock, check_output_mock):
        check_output_mock.return_value = "True"
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(IOError, moduletests.src.tcprecycle.fix, self.config_file_path)
        self.assertTrue(self.output.getvalue().endswith(
            "[UNFIXED] Failed to write config to /etc/sysctl.d/55-tcp_rw_recycle.conf\n"))
        self.assertTrue(open_mock.called)
        self.assertTrue(exists_mock.called)
        self.assertTrue(check_output_mock.called)

    @mock.patch("moduletests.src.tcprecycle.get_config_dict")
    @mock.patch("moduletests.src.tcprecycle.detect", return_value=False)
    def test_run_success(self, detect_mock, get_config_dict_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.tcprecycle.run())
        self.assertEqual(self.output.getvalue(), "Determining if aggressive TCP recycling is enabled\n"
                                                 "[SUCCESS] Aggressive TCP recycling is disabled.\n")
        self.assertTrue(detect_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.tcprecycle.get_config_dict")
    @mock.patch("moduletests.src.tcprecycle.detect", return_value=True)
    def test_run_no_remediate(self, detect_mock, get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": dict(),
                                             "REMEDIATE": False,
                                             "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.tcprecycle.run())
        self.assertTrue("[UNFIXED] Remediation impossible without sudo and --remediate.\n"
                        "-- Running as root/sudo: True\n"
                        "-- Required --remediate flag specified: False\n"
                        "[FAILURE] Aggressive TCP recycling is enabled."
                        in self.output.getvalue())
        self.assertTrue(detect_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.tcprecycle.get_config_dict")
    @mock.patch("moduletests.src.tcprecycle.detect", return_value=True)
    @mock.patch("moduletests.src.tcprecycle.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.tcprecycle.backup", return_value=True)
    @mock.patch("moduletests.src.tcprecycle.fix", return_value=True)
    @mock.patch("moduletests.src.tcprecycle.restore", return_value=True)
    def test_run_failure_isfile(self, 
                                restore_mock, 
                                fix_mock, 
                                backup_mock, 
                                isfile_mock, 
                                detect_mock, 
                                get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": {self.config_file_path: "/some/path"},
                                             "REMEDIATE": True,
                                             "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.tcprecycle.run())
        self.assertTrue("Determining if aggressive TCP recycling is enabled\n"
                        "[FAILURE] Aggressive TCP recycling is enabled."
                        in self.output.getvalue())
        self.assertTrue(restore_mock.called)
        self.assertTrue(fix_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.tcprecycle.get_config_dict")
    @mock.patch("moduletests.src.tcprecycle.detect", return_value=True)
    @mock.patch("moduletests.src.tcprecycle.os.path.isfile", return_value=False)
    @mock.patch("moduletests.src.tcprecycle.fix", return_value=True)
    def test_run_failure(self, fix_mock, isfile_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.tcprecycle.run())
        self.assertTrue("Determining if aggressive TCP recycling is enabled\n"
                        "[FAILURE] Aggressive TCP recycling is enabled."
                        in self.output.getvalue())
        self.assertTrue(fix_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.tcprecycle.get_config_dict")
    @mock.patch("moduletests.src.tcprecycle.detect", side_effect=(True, False))
    @mock.patch("moduletests.src.tcprecycle.os.path.isfile", return_value=False)
    @mock.patch("moduletests.src.tcprecycle.fix", return_value=True)
    def test_run_fix(self, fix_mock, isfile_mock, detect_mock, get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": dict(),
                                             "REMEDIATE": True,
                                             "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.tcprecycle.run())
        self.assertEqual(self.output.getvalue(), "Determining if aggressive TCP recycling is enabled\n"
                                                 "[SUCCESS] Aggressive TCP recycling is disabled after remediation. "
                                                 "Please see the logs for further details\n")
        self.assertTrue(fix_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.tcprecycle.get_config_dict")
    @mock.patch("moduletests.src.tcprecycle.detect", side_effect=Exception)
    @mock.patch("moduletests.src.tcprecycle.restore", return_value=True)
    def test_run_exception(self, restore_mock, detect_mock, get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": {self.config_file_path: "/some/path"},
                                             "REMEDIATE": True,
                                             "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.tcprecycle.run())
        self.assertTrue(restore_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.tcprecycle.get_config_dict", side_effect=IOError)
    def test_run_failure_config_exception(self, get_config_dict_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.tcprecycle.run())
        self.assertTrue(self.output.getvalue().endswith("Review the logs to determine the cause of the issue.\n"))
        self.assertTrue(get_config_dict_mock.called)
