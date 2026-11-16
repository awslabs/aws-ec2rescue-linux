# Copyright 2016-2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

"""Unit tests for supported Python runtime validation."""
from __future__ import print_function

import os
import subprocess
import sys
import unittest


class TestPythonRuntime(unittest.TestCase):
    """Test the Python runtime checks at both application entry points."""

    def run_ec2rl_main(self, hexversion):
        """Call ec2rl.main with a simulated Python version."""
        command = (
            "import ec2rl, sys; "
            "sys.hexversion = {0}; "
            "sys.exit(ec2rl.main())"
        ).format(hexversion)
        process = subprocess.Popen(
            [sys.executable, "-c", command],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = process.communicate()[0].decode("utf-8")
        return process.returncode, output

    def run_ec2rlcore_import(self, hexversion):
        """Import ec2rlcore in an isolated interpreter with a simulated version."""
        command = (
            "import sys; "
            "sys.hexversion = {0}; "
            "import ec2rlcore"
        ).format(hexversion)
        process = subprocess.Popen(
            [sys.executable, "-c", command],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = process.communicate()[0].decode("utf-8")
        return process.returncode, output

    def run_ec2rl_script(self, hexversion):
        """Run the application entry point with a simulated Python version."""
        command = (
            "import ec2rlcore, runpy, sys; "
            "sys.hexversion = {0}; "
            "sys.argv = ['ec2rl.py']; "
            "runpy.run_path('ec2rl.py', run_name='__main__')"
        ).format(hexversion)
        process = subprocess.Popen(
            [sys.executable, "-c", command],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = process.communicate()[0].decode("utf-8")
        return process.returncode, output

    def test_main_rejects_python_3_5(self):
        """Python 3 versions below 3.6 must return the retry status."""
        returncode, output = self.run_ec2rl_main(0x3050FF0)

        self.assertEqual(returncode, 201)
        self.assertEqual(
            output,
            "ec2rl requires Python 2.7+ or Python 3.6+, but running version is {0}.\n".format(
                sys.version.split()[0]
            ),
        )

    def test_ec2rlcore_rejects_python_3_5(self):
        """The defensive package check must reject Python 3.5."""
        returncode, output = self.run_ec2rlcore_import(0x3050FF0)

        self.assertEqual(returncode, 201)
        self.assertEqual(
            output,
            "ec2rl requires Python 2.7+ or Python 3.6+, but running version is {0}.\n".format(
                sys.version.split()[0]
            ),
        )

    def test_script_returns_retry_status_for_python_3_5(self):
        """The executable must return the retry status for an unsupported runtime."""
        returncode, output = self.run_ec2rl_script(0x3050FF0)

        self.assertEqual(returncode, 201)
        self.assertEqual(
            output,
            "ec2rl requires Python 2.7+ or Python 3.6+, but running version is {0}.\n".format(
                sys.version.split()[0]
            ),
        )

    def test_ec2rlcore_accepts_python_2_7(self):
        """The temporary Python 2.7 compatibility path must remain available."""
        returncode, output = self.run_ec2rlcore_import(0x2070000)

        self.assertEqual(returncode, 0)
        self.assertEqual(output, "")

    def test_ec2rlcore_accepts_python_3_6(self):
        """Python 3.6 must satisfy the Python 3 minimum."""
        returncode, output = self.run_ec2rlcore_import(0x3060000)

        self.assertEqual(returncode, 0)
        self.assertEqual(output, "")

    def test_ec2rlcore_accepts_python_3_7(self):
        """Python 3.7 must remain supported."""
        returncode, output = self.run_ec2rlcore_import(0x3070000)

        self.assertEqual(returncode, 0)
        self.assertEqual(output, "")
