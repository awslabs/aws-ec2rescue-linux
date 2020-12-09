# Copyright 2016-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
Unit tests for the duplicatefsuuid module
"""
import sys
import unittest

import mock

import moduletests.src.duplicatefsuuid

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


class Testduplicatefsuuid(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("moduletests.src.duplicatefsuuid.subprocess.check_output")
    def test_duplicatefsuuid_get_fs_uuid_dict(self, subprocess_mock):
        """Test that given sample blkid output, get_fs_uuid_dict() returns the expected dict."""
        subprocess_mock.return_value = "/dev/xvda1: UUID=\"84691ef1-f2b5-467a-adf6-ddccbacdd703\"\n" \
                                       "/dev/xvdf1: UUID=\"84691ef1-f2b5-467a-adf6-ddccbacdd703\"\n" \
                                       "/dev/xvdg1: UUID=\"0f2878a3-1465-4961-9323-d4769c28e995\""
        fs_uuid_dict = moduletests.src.duplicatefsuuid.get_fs_uuid_dict()
        expected_fs_uuid_dict = {"84691ef1-f2b5-467a-adf6-ddccbacdd703": ["/dev/xvda1", "/dev/xvdf1"],
                                 "0f2878a3-1465-4961-9323-d4769c28e995": ["/dev/xvdg1"]}
        self.assertEqual(fs_uuid_dict, expected_fs_uuid_dict)
        self.assertTrue(subprocess_mock.called)

    @mock.patch("moduletests.src.duplicatefsuuid.get_fs_uuid_dict", side_effect=OSError)
    def test_duplicatefsuuid_run_exception(self, get_fs_uuid_dict_mock):
        """Test that run() returns False when an unhandled exception is raised."""
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.duplicatefsuuid.run())
        self.assertTrue(self.output.getvalue().endswith("Review the logs to determine the cause of the issue.\n"))
        self.assertTrue(get_fs_uuid_dict_mock.called)

    @mock.patch("moduletests.src.duplicatefsuuid.get_fs_uuid_dict")
    def test_duplicatefsuuid_run_success(self, get_fs_uuid_dict_mock):
        """Test that run() returns True executes successfully, verifying the dict does not contain a duplicate."""
        get_fs_uuid_dict_mock.return_value = {"84691ef1-f2b5-467a-adf6-ddccbacdd703": ["/dev/xvda1"],
                                              "0f2878a3-1465-4961-9323-d4769c28e995": ["/dev/xvdf1"]}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.duplicatefsuuid.run())
        self.assertTrue("[SUCCESS] No duplicate filesystem UUIDs found.\n" in self.output.getvalue())
        self.assertTrue(get_fs_uuid_dict_mock.called)

    @mock.patch("moduletests.src.duplicatefsuuid.get_fs_uuid_dict")
    def test_duplicatefsuuid_run_failure(self, get_fs_uuid_dict_mock):
        """Test that run() returns True executes successfully, verifying the dict does contain a duplicate."""
        get_fs_uuid_dict_mock.return_value = {"84691ef1-f2b5-467a-adf6-ddccbacdd703": ["/dev/xvda1", "/dev/xvdf1"],
                                              "0f2878a3-1465-4961-9323-d4769c28e995": ["/dev/xvdg1"]}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.duplicatefsuuid.run())
        self.assertTrue("[FAILURE] Duplicate UUID, 84691ef1-f2b5-467a-adf6-ddccbacdd703, found on the following"
                        " filesystems: /dev/xvda1, /dev/xvdf1\n" in self.output.getvalue())
        self.assertTrue(get_fs_uuid_dict_mock.called)
