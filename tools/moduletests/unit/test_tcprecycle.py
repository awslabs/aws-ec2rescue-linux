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
Unit tests for the tcprecycle module
"""
import os
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

# builtins was named __builtin__ in Python 2 so accommodate the change for the purposes of mocking the open call
if sys.version_info >= (3,):
    builtins_name = "builtins"
else:
    builtins_name = "__builtin__"


class Testtcprecycle(unittest.TestCase):

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("subprocess.check_output")
    def test_detect_noproblem(self, check_output_mock):
        check_output_mock.return_value = b"net.ipv4.tcp_tw_recycle = 0"
        self.assertFalse(moduletests.src.tcprecycle.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output")
    def test_detect_problem(self, check_output_mock):
        check_output_mock.return_value = b"net.ipv4.tcp_tw_recycle = 1"
        self.assertTrue(moduletests.src.tcprecycle.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch.dict(os.environ, {"EC2RL_SUDO": "True"})
    @mock.patch("subprocess.check_call")
    @mock.patch("moduletests.src.tcprecycle.open", mock.mock_open(read_data="stuff"))
    def test_sudo_true(self, check_call_mock):
        check_call_mock.return_value = "True"
        self.assertTrue(moduletests.src.tcprecycle.fix())
        self.assertTrue(check_call_mock.called)

    @mock.patch.dict(os.environ, {"EC2RL_SUDO": "False"})
    def test_sudo_false(self):
        self.assertFalse(moduletests.src.tcprecycle.fix())

    @mock.patch.dict(os.environ, {"EC2RL_SUDO": "True"})
    @mock.patch("subprocess.check_call",
                side_effect=subprocess.CalledProcessError
                    ("1", "test", "/etc/sysctl.d/55-tcp_rw_recycle.conf: no such file or directory"))
    def test_fix_cpe(self, check_call_mock):
        self.assertRaises(Exception, moduletests.src.tcprecycle.fix())
        self.assertTrue(check_call_mock.called)

    @mock.patch.dict(os.environ, {"EC2RL_SUDO": "True"})
    @mock.patch("subprocess.check_call")
    def test_fix_writefail(self, check_call_mock):
        with mock.patch("moduletests.src.tcprecycle.open", mock.mock_open, create="True") as mocked_open:
            mocked_open.side_effect = IOError()
            check_call_mock.return_value = "True"
            self.assertRaises(Exception, moduletests.src.tcprecycle.fix())
            self.assertTrue(check_call_mock.called)

    def test_print_fixed(self):
        with contextlib.redirect_stdout(self.output):
            moduletests.src.tcprecycle.print_results(results="fixed")
        self.assertEqual(len(self.output.getvalue()), 223)

    def test_print_else(self):
        with contextlib.redirect_stdout(self.output):
            moduletests.src.tcprecycle.print_results(results="else")
        self.assertEqual(len(self.output.getvalue()), 176)

    @mock.patch.dict(os.environ, {"remediate": "True"})
    @mock.patch("moduletests.src.tcprecycle.detect", return_value=False)
    def test_run_success(self, detect_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.tcprecycle.run())
        self.assertEqual(len(self.output.getvalue()), 219)

    @mock.patch("moduletests.src.tcprecycle.detect", return_value=True)
    def test_run_no_remediate(self, detect_mock):
        self.assertFalse(moduletests.src.tcprecycle.run())

    @mock.patch.dict(os.environ, {"remediate": "True", "EC2RL_SUDO": "True"})
    @mock.patch("moduletests.src.tcprecycle.detect", return_value=(True, True))
    @mock.patch("moduletests.src.tcprecycle.fix", return_value=True)
    def test_run_failure(self, detect_mock, fix_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.tcprecycle.run())
        self.assertEqual(len(self.output.getvalue()), 529)

    @mock.patch.dict(os.environ, {"remediate": "True", "EC2RL_SUDO": "True"})
    @mock.patch("moduletests.src.tcprecycle.detect", side_effect=(True, False))
    @mock.patch("moduletests.src.tcprecycle.fix", return_value=True)
    def test_run_fix(self, detect_mock, fix_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.tcprecycle.run())
        self.assertEqual(len(self.output.getvalue()), 277)

    @mock.patch.dict(os.environ, {"remediate":"True", "EC2RL_SUDO":"True"})
    @mock.patch("moduletests.src.tcprecycle.detect", side_effect=Exception)
    def test_run_exit(self, detect_mock):
        with self.assertRaises(SystemExit) as ex:
            self.assertRaises(Exception, moduletests.src.tcprecycle.run())
        self.assertEqual(ex.exception.code, 0)
