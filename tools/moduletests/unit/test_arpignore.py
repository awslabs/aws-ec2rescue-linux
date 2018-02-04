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

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("subprocess.check_output")
    def test_detect_noproblem(self, check_output_mock):
        check_output_mock.return_value = b"arp_ignore = 0"
        self.assertFalse(moduletests.src.arpignore.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output")
    def test_detect_problem(self, check_output_mock):
        check_output_mock.return_value = b"arp_ignore = 1"
        self.assertTrue(moduletests.src.arpignore.detect())
        self.assertTrue(check_output_mock.called)

    @mock.patch.dict(os.environ, {"EC2RL_SUDO": "False"})
    def test_sudo_false(self):
        self.assertFalse(moduletests.src.arpignore.fix())

    def test_fix_sysctl(self):
        self.assertTrue(moduletests.src.arpignore.sysctlfix(eth="arp_ignore = 1"))

    @mock.patch("moduletests.src.arpignore.open", mock.mock_open(read_data="stuff"))
    def test_fix_write_ex(self):
        self.assertTrue(moduletests.src.arpignore.writefix(eth="arp_ignore = 1"))

    @mock.patch.dict(os.environ, {"EC2RL_SUDO": "True"})
    @mock.patch("moduletests.src.arpignore.sysctlget", return_value=(["arp_ignore = 1"]))
    def test_fix_writefail(self, sysctlget_mock):
        with mock.patch("moduletests.src.arpignore.open", mock.mock_open, create="True") as mocked_open:
            mocked_open.side_effect = IOError()
            with self.assertRaises(SystemExit) as ex:
                self.assertRaises(Exception, moduletests.src.arpignore.fix())
            self.assertEqual(ex.exception.code, 0)

    def test_print_fixed(self):
        with contextlib.redirect_stdout(self.output):
            moduletests.src.arpignore.print_results(results="fixed")
        self.assertEqual(len(self.output.getvalue()), 187)

    def test_print_else(self):
        with contextlib.redirect_stdout(self.output):
            moduletests.src.arpignore.print_results(results="else")
        self.assertEqual(len(self.output.getvalue()), 175)

    @mock.patch.dict(os.environ, {"remediate": "True"})
    @mock.patch("moduletests.src.arpignore.detect", return_value=False)
    def test_run_success(self, detect_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpignore.run())
        self.assertEqual(len(self.output.getvalue()), 230)

    @mock.patch("moduletests.src.arpignore.detect", return_value=True)
    def test_run_no_remediate(self, detect_mock):
        self.assertFalse(moduletests.src.arpignore.run())

    @mock.patch.dict(os.environ, {"remediate": "True", "EC2RL_SUDO": "True"})
    @mock.patch("moduletests.src.arpignore.detect", return_value=(True, True))
    @mock.patch("moduletests.src.arpignore.fix", return_value=True)
    def test_run_failure(self, detect_mock, fix_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.arpignore.run())
        self.assertEqual(len(self.output.getvalue()), 659)

    @mock.patch.dict(os.environ, {"remediate": "True", "EC2RL_SUDO": "True"})
    @mock.patch("moduletests.src.arpignore.detect", side_effect=(True, False))
    @mock.patch("moduletests.src.arpignore.fix", return_value=True)
    def test_run_fix(self, detect_mock, fix_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.arpignore.run())
        self.assertEqual(len(self.output.getvalue()), 248)

    @mock.patch.dict(os.environ, {"remediate": "True", "EC2RL_SUDO": "True"})
    @mock.patch("moduletests.src.arpignore.detect", side_effect=Exception)
    def test_run_exit(self, detect_mock):
        with self.assertRaises(SystemExit) as ex:
            self.assertRaises(Exception, moduletests.src.arpignore.run())
        self.assertEqual(ex.exception.code, 0)

    @mock.patch.dict(os.environ, {"remediate": "True", "EC2RL_SUDO": "True"})
    @mock.patch("moduletests.src.arpignore.sysctlget", return_value=(["arp_ignore = 1"]))
    @mock.patch("moduletests.src.arpignore.sysctlfix", side_effect=Exception("failure"))
    def test_sysctl_exception(self, sysctlget_mock, exception_mock):
        with self.assertRaises(SystemExit) as ex:
            self.assertRaises(Exception, moduletests.src.arpignore.fix)
        self.assertEqual(ex.exception.code, 0)
