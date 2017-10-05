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

"""Unit tests for "prediag" module."""
import requests
import unittest

import mock
import responses

import ec2rlcore.prediag


class TestPrediag(unittest.TestCase):
    """Testing class for "prediag" unit tests."""

    @responses.activate
    def test_prediag_verify_metadata(self):
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", status=200)

        resp = ec2rlcore.prediag.verify_metadata()

        self.assertTrue(resp)

    @mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError)
    def test_prediag_verify_metadata_connerror(self, mock_get):
        self.assertFalse(ec2rlcore.prediag.verify_metadata())
        self.assertTrue(mock_get.called)

    @responses.activate
    def test_prediag_get_virt_type(self):
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/profile", status=200, body="hvm")

        resp = ec2rlcore.prediag.get_virt_type()

        self.assertEqual(resp, "hvm")

    @responses.activate
    def test_prediag_get_virt_type_error(self):
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/profile", status=404, body="hvm")

        resp = ec2rlcore.prediag.get_virt_type()

        self.assertEqual(resp, "ERROR")

    @mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError)
    def test_prediag_get_virt_type_connerror(self, mock_get):
        with self.assertRaises(ec2rlcore.prediag.PrediagConnectionError):
            ec2rlcore.prediag.get_virt_type()
        self.assertTrue(mock_get.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="Amazon Linux AMI release 2016.09"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_alami(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "alami")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="Red Hat Enterprise Linux Server release 7.0"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_rhel(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "rhel")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="CentOS Linux release 7.1.1503"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_cent(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "rhel")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="junk"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_sysrelease_unknown(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "unknown for /etc/system-release")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="SUSE Linux Enterprise Server 10 (x86_64)"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, True))
    def test_prediag_os_suse(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "suse")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="junk"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, True))
    def test_prediag_os_suse_unknown(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "unknown for /etc/SuSE-release")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="DISTRIB_ID=Ubuntu"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, False, True))
    def test_prediag_os_ubuntu(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "ubuntu")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="junk"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, False, True))
    def test_prediag_os_lsb_unknown(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "unknown for /etc/lsb-release")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="Amazon Linux AMI release 2012.09"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, False, False, True))
    def test_prediag_os_old_alami(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "alami")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="Red Hat Enterprise Linux Server release 5.11"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, False, False, True))
    def test_prediag_os_old_rhel(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "rhel")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="junk"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, False, False, True))
    def test_prediag_os_etc_issue_unknown(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "unknown for /etc/issue")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data='PRETTY_NAME="Amazon Linux AMI 2017.03"'))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, False, False, False, True))
    def test_prediag_osrelease_alami(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "alami")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data='PRETTY_NAME="SUSE Linux Enterprise Server 12 SP2"'))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, False, False, False, True))
    def test_prediag_osrelease_suse(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "suse")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="junk"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, False, False, False, True))
    def test_prediag_osrelease_unknown(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "unknown for /etc/os-release")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.os.path.isfile", side_effect=(False, False, False, False, False))
    def test_prediag_os_unknown(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "unknown")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.os.getegid", return_value=0)
    def test_prediag_check_root(self, mock_getegid):
        self.assertTrue(ec2rlcore.prediag.check_root())
        self.assertTrue(mock_getegid.called)

    def test_prediag_get_net_driver(self):
        with mock.patch("ec2rlcore.prediag.os.listdir") as mockdir:
            mockdir.return_value = ["eth0", "lo"]
            with mock.patch("ec2rlcore.prediag.os.readlink") as mocklink:
                mocklink.return_value = "../../../../module/ixgbevf"
                self.assertEqual(ec2rlcore.prediag.get_net_driver(), "ixgbevf")

    def test_prediag_get_net_driver_fail(self):
        with mock.patch("ec2rlcore.prediag.os.listdir") as mockdir:
            mockdir.return_value = ["lo"]
            self.assertEqual(ec2rlcore.prediag.get_net_driver(), "Unknown")

    @mock.patch("ec2rlcore.prediag.os.readlink", side_effect=OSError)
    def test_prediag_get_net_driver_oserror_unknown(self, mock_readlink):
        self.assertEqual(ec2rlcore.prediag.get_net_driver(), "Unknown")
        self.assertTrue(mock_readlink.called)
