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
Unit tests for the arpcache module
"""
import os
import subprocess
import sys
import unittest

import mock

import moduletests.src.arpcache

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


class TestArpcache(unittest.TestCase):
    config_file_path = "/etc/sysctl.d/55-arp-gc_thresh1.conf"

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("subprocess.check_output")
    def test_detect_noproblem(self, check_output_mock):
        check_output_mock.return_value = "net.ipv4.neigh.default.gc_thresh1 = 0"
        self.assertFalse(moduletests.src.arpcache.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output")
    def test_detect_problem(self, check_output_mock):
        check_output_mock.return_value = "net.ipv4.neigh.default.gc_thresh1 = 1"
        self.assertTrue(moduletests.src.arpcache.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        "1", "test", "/etc/sysctl.d/55-arp-gc_thresh1.conf: no such file or directory"))
    def test_fix_cpe(self, check_output_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(subprocess.CalledProcessError, moduletests.src.arpcache.fix, self.config_file_path)
        self.assertTrue(self.output.getvalue().endswith(
            "[UNFIXED] 'sysctl -w net.ipv4.neigh.default.gc_thresh1=0' failed for running system\n"))
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.arpcache.os.path.exists", side_effect=[False])
    @mock.patch("moduletests.src.arpcache.open", mock.mock_open(read_data="stuff"))
    def test_fix_exists_sudo_true(self, check_output_mock, exists_mock):
        check_output_mock.return_value = "True"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpcache.fix(self.config_file_path))
        self.assertTrue(self.output.getvalue().endswith(
            "[FIXED] set net.ipv4.neigh.default.gc_thresh1=0 for running system\n"
            "[FIXED] net.ipv4.neigh.default.gc_thresh1=0 in /etc/sysctl.d/55-arp-gc_thresh1.conf\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(exists_mock.called)

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.arpcache.os.path.exists", side_effect=[True])
    @mock.patch("moduletests.src.arpcache.open", mock.mock_open(read_data="net.ipv4.neigh.default.gc_thresh1 = 0\n"
                                                                          "something else\n"))
    def test_fix_sudo_true(self, check_output_mock, exists_mock):
        check_output_mock.return_value = "True"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpcache.fix(self.config_file_path))
        self.assertTrue(self.output.getvalue().endswith(
            "[FIXED] set net.ipv4.neigh.default.gc_thresh1=0 for running system\n"
            "[FIXED] net.ipv4.neigh.default.gc_thresh1=0 in /etc/sysctl.d/55-arp-gc_thresh1.conf\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(exists_mock.called)

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.arpcache.os.path.exists", side_effect=[True])
    @mock.patch("moduletests.src.arpcache.open", mock.mock_open(read_data="net.ipv4.neigh.default.gc_thresh1 = 0\n"
                                                                          "net.ipv4.neigh.default.gc_thresh1 = 0\n"))
    def test_fix_sudo_true_found_twice(self, check_output_mock, exists_mock):
        check_output_mock.return_value = "True"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpcache.fix(self.config_file_path))
        self.assertTrue(self.output.getvalue().endswith(
            "[FIXED] set net.ipv4.neigh.default.gc_thresh1=0 for running system\n"
            "[FIXED] net.ipv4.neigh.default.gc_thresh1=0 in /etc/sysctl.d/55-arp-gc_thresh1.conf\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(exists_mock.called)

    @mock.patch("subprocess.check_output")
    @mock.patch("moduletests.src.arpcache.os.path.exists", side_effect=[False])
    @mock.patch("moduletests.src.arpcache.open", side_effect=IOError)
    def test_fix_writefail(self, open_mock, exists_mock, check_output_mock):
            check_output_mock.return_value = "True"
            with contextlib.redirect_stdout(self.output):
                self.assertRaises(IOError, moduletests.src.arpcache.fix, self.config_file_path)
            self.assertTrue(check_output_mock.called)
            self.assertTrue(exists_mock.called)
            self.assertTrue(open_mock.called)
            self.assertTrue(self.output.getvalue().endswith(
                "[UNFIXED] Failed to write config to /etc/sysctl.d/55-arp-gc_thresh1.conf\n"))

    @mock.patch("moduletests.src.arpcache.detect", return_value=False)
    def test_run_success(self, detect_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpcache.run())
        self.assertTrue(self.output.getvalue().endswith("Determining if aggressive ARP caching is enabled\n"
                                                        "[SUCCESS] Aggressive arp caching is disabled.\n"))
        self.assertTrue(detect_mock.called)

    @mock.patch("moduletests.src.arpcache.get_config_dict")
    @mock.patch("moduletests.src.arpcache.detect", return_value=True)
    def test_run_no_remediate(self, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": False,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            moduletests.src.arpcache.run()
        self.assertTrue("[UNFIXED] Remediation impossible without sudo and --remediate.\n"
                        "-- Running as root/sudo: True\n"
                        "-- Required --remediate flag specified: False\n"
                        "[FAILURE] Aggressive arp caching is enabled."
                        in self.output.getvalue())
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpcache.get_config_dict")
    @mock.patch("moduletests.src.arpcache.detect", return_value=True)
    @mock.patch("moduletests.src.arpcache.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.arpcache.backup", return_value=True)
    @mock.patch("moduletests.src.arpcache.fix", return_value=True)
    @mock.patch("moduletests.src.arpcache.restore", return_value=True)
    def test_run_failure_isfile(self, restore_mock, fix_mock, backup_mock, isfile_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": {self.config_file_path: "/some/path"},
                                    "REMEDIATE": True,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.arpcache.run())
        self.assertTrue("Determining if aggressive ARP caching is enabled\n"
                        "[FAILURE] Aggressive arp caching is enabled. "
                        "This can cause issues communicating with instances in the same subnet"
                        in self.output.getvalue())
        self.assertTrue(restore_mock.called)
        self.assertTrue(fix_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpcache.get_config_dict")
    @mock.patch("moduletests.src.arpcache.detect", return_value=True)
    @mock.patch("moduletests.src.arpcache.os.path.isfile", return_value=False)
    @mock.patch("moduletests.src.arpcache.fix", return_value=True)
    def test_run_failure(self, fix_mock, isfile_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.arpcache.run())
        self.assertTrue("Determining if aggressive ARP caching is enabled\n"
                        "[FAILURE] Aggressive arp caching is enabled. "
                        "This can cause issues communicating with instances in the same subnet"
                        in self.output.getvalue())
        self.assertTrue(fix_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpcache.get_config_dict")
    @mock.patch("moduletests.src.arpcache.detect", side_effect=(True, False))
    @mock.patch("moduletests.src.arpcache.os.path.isfile", return_value=False)
    @mock.patch("moduletests.src.arpcache.fix", return_value=True)
    def test_run_fix(self, fix_mock, isfile_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpcache.run())
        self.assertTrue(self.output.getvalue().endswith("Determining if aggressive ARP caching is enabled\n"
                                                        "[SUCCESS] Aggressive arp caching is disabled after "
                                                        "remediation. Please see the logs for further details\n"))
        self.assertTrue(fix_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.arpcache.get_config_dict")
    @mock.patch("moduletests.src.arpcache.detect", side_effect=Exception)
    @mock.patch("moduletests.src.arpcache.restore", return_value=True)
    def test_run_detect_exception(self, restore_mock, detect_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                                  "LOG_DIR": "/var/tmp/ec2rl",
                                                  "BACKED_FILES": {self.config_file_path: "/some/path"},
                                                  "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.arpcache.run())
        self.assertTrue(detect_mock.called)
        self.assertTrue(config_mock.called)
        self.assertTrue(restore_mock.called)

    @mock.patch("moduletests.src.arpcache.get_config_dict", side_effect=Exception)
    def test_run_config_exception(self, config_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.arpcache.run())
        self.assertTrue(config_mock.called)
