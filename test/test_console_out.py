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

"""Unit tests for "summary" module."""
import os
import re
import sys
import unittest

try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

import ec2rlcore.console_out
import ec2rlcore.module

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib


class TestConsoleOut(unittest.TestCase):
    """Testing class for "console_out" unit tests."""
    module_path = ""
    module = ""

    argv_backup = sys.argv
    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    if os.path.isdir(_callp):
        callpath = _callp
    else:
        callpath = os.path.split(_callp)[0]

    def setUp(self):
        """Setup the module that will be used for the tests."""
        ec2rlcore.console_out._first_module = True
        self.module_path = os.path.join(self.callpath, "test/modules/mod.d/ex.yaml")
        self.module = ec2rlcore.module.get_module(self.module_path)

    def test_notify_module_running_first_module_prepends_header(self):
        """
        notify_module_running() on first module call must emit the header and omit the prepended comma
        """
        output = StringIO()
        with contextlib.redirect_stdout(output):
            ec2rlcore.console_out.notify_module_running(self.module)
        self.assertEqual(output.getvalue(), "Running Modules:\nex")
        output.close()

    def test_notify_module_running_sets_first_module_flag(self):
        """
        notify_module_running() on first module call set summary._first_module to False
        """
        # mod = self.TestModule(name="test1", placement="test")
        with open(os.devnull, "w") as capture_stream:
            with contextlib.redirect_stdout(capture_stream):
                ec2rlcore.console_out.notify_module_running(self.module)

            self.assertFalse(ec2rlcore.console_out._first_module,
                             msg="summary._first_module must be False after first module")

    def test_notify_module_running_prepends_comma(self):
        """
        notify_module_running() on not first module call must prepend a comma to module name
        """
        ec2rlcore.console_out._first_module = False
        # mod = self.TestModule(name="test_module", placement="test")
        output = StringIO()
        with contextlib.redirect_stdout(output):
            ec2rlcore.console_out.notify_module_running(self.module)

        self.assertEqual(output.getvalue(), ", ex")
        output.close()
