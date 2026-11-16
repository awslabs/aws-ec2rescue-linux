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

"""Unit tests for the vendored Python dependency import chain."""
import os
import subprocess
import sys
import unittest


class TestVendoredDependencies(unittest.TestCase):
    """Test the independent six namespaces and their consumers."""

    def run_with_vendored_dependencies(self, command):
        """Run Python with the same vendored dependency path order as ec2rl."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        version_directory = "python3" if sys.version_info[0] >= 3 else "python2"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            [
                os.path.join(project_root, "lib", version_directory),
                os.path.join(project_root, "lib"),
            ]
        )
        process = subprocess.Popen(
            [sys.executable, "-c", command],
            cwd=project_root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = process.communicate()[0].decode("utf-8")
        return process.returncode, output

    def test_six_versions(self):
        """All runtime copies of six must use the supported version."""
        command = (
            "import six; "
            "from botocore.vendored import six as botocore_six; "
            "from urllib3.packages import six as urllib3_six; "
            "print('|'.join((six.__version__, botocore_six.__version__, "
            "urllib3_six.__version__)))"
        )
        returncode, output = self.run_with_vendored_dependencies(command)

        self.assertEqual(returncode, 0)
        self.assertEqual(output, "1.17.0|1.17.0|1.17.0\n")

    def test_six_moves_imports(self):
        """Each vendored namespace must provide its virtual moves package."""
        command = (
            "from botocore.vendored.six.moves import urllib_parse; "
            "from six.moves import urllib_parse; "
            "from urllib3.packages.six.moves import http_client"
        )
        returncode, output = self.run_with_vendored_dependencies(command)

        self.assertEqual(returncode, 0)
        self.assertEqual(output, "")

    def test_http_and_aws_sdk_imports(self):
        """The complete vendored HTTP and AWS SDK dependency chain must import."""
        command = "import boto3, botocore, requests, urllib3"
        returncode, _output = self.run_with_vendored_dependencies(command)

        self.assertEqual(returncode, 0)

    def test_botocore_content_type_encoding(self):
        """Botocore must parse Content-Type headers without the removed cgi module."""
        command = (
            "from botocore.utils import get_encoding_from_headers; "
            "assert get_encoding_from_headers("
            "{'content-type': 'text/plain; charset=\"UTF-8\"'}) == 'UTF-8'; "
            "assert get_encoding_from_headers("
            "{'content-type': 'text/plain'}) == 'ISO-8859-1'; "
            "assert get_encoding_from_headers("
            "{'content-type': 'application/json'}) is None; "
            "assert get_encoding_from_headers("
            "{\"content-type\": \"text/plain; charset*=utf-8''UTF-8\"}) == 'UTF-8'; "
            "assert get_encoding_from_headers("
            "{'content-type': 'application/json; note=\"text\"'}) is None"
        )
        returncode, output = self.run_with_vendored_dependencies(command)

        self.assertEqual(returncode, 0)
        self.assertEqual(output, "")
