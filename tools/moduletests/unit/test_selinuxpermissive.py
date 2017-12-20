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
Unit tests for the selinuxpermissive module
"""
import os
import subprocess
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

# builtins was named __builtin__ in Python 2 so accommodate the change for the purposes of mocking the open call
if sys.version_info >= (3,):
    builtins_name = "builtins"
else:
    builtins_name = "__builtin__"


class Testselinuxpermissive(unittest.TestCase):

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("moduletests.src.selinuxpermissive.open", mock.mock_open(read_data="stuff"))
    def test_readfile(self):
        self.assertEqual(moduletests.src.selinuxpermissive.readfile(), "stuff")

    @mock.patch("moduletests.src.selinuxpermissive.open", side_effect=Exception)
    def test_readfile_failure(self, isfile_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.selinuxpermissive.readfile()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.selinuxpermissive.os.path.isfile", return_value=False)
    def test_detect_noselinux(self, readfile_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.selinuxpermissive.detect()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.selinuxpermissive.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.readfile", return_value="SELINUX=enforcing")
    def test_detect_problem(self, isfile_mock, readfile_mock):
        self.assertTrue(moduletests.src.selinuxpermissive.detect())

    @mock.patch("moduletests.src.selinuxpermissive.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.readfile", return_value="SELINUX=permissive")
    def test_detect_noproblem(self, isfile_mock, readfile_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.selinuxpermissive.detect()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.selinuxpermissive.shutil.copyfile", return_value=True)
    def test_backup_success(self, copy_mock):
        self.assertTrue(moduletests.src.selinuxpermissive.backup())

    @mock.patch("moduletests.src.selinuxpermissive.shutil.copyfile", side_effect=Exception)
    def test_backup_failure(self, copy_mock):
        with self.assertRaises(SystemExit) as ex:
            self.assertRaises(Exception, moduletests.src.selinuxpermissive.backup())
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.selinuxpermissive.readfile", return_value="SELINUX=enforcing")
    @mock.patch("moduletests.src.selinuxpermissive.open", mock.mock_open(read_data="stuff"))
    def test_fix_success(self, readfile_mock):
        self.assertTrue(moduletests.src.selinuxpermissive.fix())

    @mock.patch("moduletests.src.selinuxpermissive.readfile", return_value="SELINUX=enforcing")
    @mock.patch("moduletests.src.selinuxpermissive.open", side_effect=Exception)
    def test_fix_exception(self, readfile_mock, open_mock):
        with self.assertRaises(SystemExit) as ex:
            self.assertRaises(Exception, moduletests.src.selinuxpermissive.fix())
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.selinuxpermissive.detect", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.backup", return_value=True)
    @mock.patch("moduletests.src.selinuxpermissive.fix", return_value=True)
    def test_run_success(self, detect_mock, backup_mock, fix_mock):
        self.assertTrue(moduletests.src.selinuxpermissive.run())

    @mock.patch("moduletests.src.selinuxpermissive.detect", side_effect=Exception)
    def test_run_failure(self, detect_mock):
        with self.assertRaises(SystemExit) as ex:
            self.assertRaises(Exception, moduletests.src.selinuxpermissive.run())
        self.assertEqual(ex.exception.code, 0)
