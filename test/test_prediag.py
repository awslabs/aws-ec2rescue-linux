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

"""Unit tests for "prediag" module."""
import os
import sys
import unittest

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

import mock
import requests
import responses

import ec2rlcore.prediag


class TestPrediag(unittest.TestCase):
    """Testing class for "prediag" unit tests."""
    @staticmethod
    def return_true(*args, **kwargs):
        return True

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output = None

    @responses.activate
    def test_prediag_verify_metadata(self):
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", status=200)
        resp = ec2rlcore.prediag.verify_metadata()
        self.assertTrue(resp)

    @mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError)
    def test_prediag_verify_metadata_connerror(self, mock_get):
        self.assertFalse(ec2rlcore.prediag.verify_metadata())
        self.assertTrue(mock_get.called)

    def test_prediag_is_nitro_true(self):
        open_mock = mock.mock_open(read_data="i-deadbeef\n")
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("ec2rlcore.prediag.open", open_mock):
            self.assertTrue(ec2rlcore.prediag.is_nitro())
        self.assertTrue(open_mock.called)

    def test_prediag_is_nitro_false_instance_not_in_asset(self):
        open_mock = mock.mock_open(read_data="34589732\n")
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("ec2rlcore.prediag.open", open_mock):
            self.assertFalse(ec2rlcore.prediag.is_nitro())
        self.assertTrue(open_mock.called)

    @mock.patch("ec2rlcore.prediag.open", side_effect=IOError("No such file or directory"))
    def test_prediag_is_nitro_false_no_asset_file(self, isfile_mock):
        self.assertFalse(ec2rlcore.prediag.is_nitro())
        self.assertTrue(isfile_mock.called)

    @responses.activate
    def test_prediag_is_an_instance_true_xen(self):
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document", status=200)
        open_mock = mock.mock_open(read_data="ec2SomeUUIDWouldNormallyGoHere\n")
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("ec2rlcore.prediag.open", open_mock):
            self.assertTrue(ec2rlcore.prediag.is_an_instance())
        self.assertTrue(open_mock.called)

    @mock.patch("ec2rlcore.prediag.open", side_effect=IOError("No such file or directory"))
    def test_prediag_is_an_instance_false_no_sys_hypervisor_uuid(self, isfile_mock):
        self.assertFalse(ec2rlcore.prediag.is_an_instance())
        self.assertTrue(isfile_mock.called)

    def test_prediag_is_an_instance_false_ec2_not_in_uuid(self):
        open_mock = mock.mock_open(read_data="SomeUUIDWouldNormallyGoHere\n")
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("ec2rlcore.prediag.open", open_mock):
            self.assertFalse(ec2rlcore.prediag.is_an_instance())
        self.assertTrue(open_mock.called)

    @mock.patch("requests.get", side_effect=requests.RequestException())
    def test_prediag_is_an_instance_false_requests_exception(self, get_mock):
        open_mock = mock.mock_open(read_data="ec2SomeUUIDWouldNormallyGoHere\n")
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("ec2rlcore.prediag.open", open_mock):
            self.assertFalse(ec2rlcore.prediag.is_an_instance())
        self.assertTrue(open_mock.called)
        self.assertTrue(get_mock.called)

    @responses.activate
    @mock.patch('ec2rlcore.prediag.is_nitro')
    def test_prediag_get_virt_type_xen(self, mock_nitro):
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/profile", status=200, body="default-hvm")
        mock_nitro.return_value = False
        resp = ec2rlcore.prediag.get_virt_type()
        self.assertEqual(resp, "default-hvm")

    @responses.activate
    @mock.patch('ec2rlcore.prediag.is_nitro')
    def test_prediag_get_virt_type_error(self, mock_nitro):
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/profile", status=404, body="hvm")
        mock_nitro.return_value = False
        resp = ec2rlcore.prediag.get_virt_type()
        self.assertEqual(resp, "ERROR")

    @mock.patch('requests.get')
    @mock.patch('ec2rlcore.prediag.is_nitro')
    def test_prediag_get_virt_type_connerror(self, mock_get, mock_nitro):
        mock_nitro.return_value = False
        with self.assertRaises(ec2rlcore.prediag.PrediagConnectionError):
            mock_get.side_effect = requests.exceptions.ConnectionError
            ec2rlcore.prediag.get_virt_type()
        self.assertTrue(mock_get.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="Amazon Linux AMI release 2016.09"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_alami(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "alami")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="Amazon Linux release 2 (Karoo)"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_alami2_lts_release_new(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "alami2")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="Amazon Linux 2"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_alami2_lts_release(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "alami2")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open",
                mock.mock_open(read_data="Amazon Linux release 2.0 (2017.12) LTS Release Candidate"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_alami2_release_candidate(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "alami2")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="Red Hat Enterprise Linux Server release 7.0"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_rhel(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "rhel")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="CentOS Linux release 7.1.1503"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_cent7(self, mock_isfile):
        self.assertEqual(ec2rlcore.prediag.get_distro(), "rhel")
        self.assertTrue(mock_isfile.called)

    @mock.patch("ec2rlcore.prediag.open", mock.mock_open(read_data="CentOS release 6.9 (Final)\n"))
    @mock.patch("ec2rlcore.prediag.os.path.isfile", returns=True)
    def test_prediag_os_cent6(self, mock_isfile):
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

    @mock.patch("os.path.isdir", side_effect=[False])
    @mock.patch("os.path.isfile", side_effect=[True])
    @mock.patch("os.path.exists", side_effect=[False, True])
    @mock.patch("shutil.copy2", side_effect=[True])
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("os.stat")
    def test_module_functions_backup_isfile(self, stat_mock, chown_mock, copy2_mock, exists_mock, isfile_mock,
                                            isdir_mock):
        stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0)
        backed_files = {}
        self.assertEqual(ec2rlcore.prediag.backup("/test", backed_files, "/tmp"), "/tmp/test")
        self.assertEqual(backed_files, {"/test": "/tmp/test"})
        self.assertTrue(isdir_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(exists_mock.called)
        self.assertTrue(copy2_mock.called)
        self.assertTrue(chown_mock.called)
        self.assertTrue(stat_mock.called)

    @mock.patch("os.path.isdir", side_effect=[False])
    @mock.patch("os.path.isfile", side_effect=[True])
    @mock.patch("os.path.exists", side_effect=[False, False])
    @mock.patch("os.makedirs", side_effect=[True])
    @mock.patch("shutil.copy2", side_effect=[True])
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("os.stat")
    def test_module_functions_backup_isfile_makedirs(self, stat_mock, chown_mock, copy2_mock, makedirs_mock,
                                                     exists_mock, isfile_mock, isdir_mock):
        stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0)
        backed_files = {}
        self.assertEqual(ec2rlcore.prediag.backup("/test", backed_files, "/tmp"), "/tmp/test")
        self.assertEqual(backed_files, {"/test": "/tmp/test"})
        self.assertTrue(isdir_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(exists_mock.called)
        self.assertTrue(makedirs_mock.called)
        self.assertTrue(copy2_mock.called)
        self.assertTrue(chown_mock.called)
        self.assertTrue(stat_mock.called)

    @mock.patch("os.path.isdir", side_effect=[True, True])
    @mock.patch("os.path.exists", side_effect=[False, True])
    @mock.patch("shutil.copytree", side_effect=[True])
    @mock.patch("os.walk")
    @mock.patch("os.path.islink", side_effect=[False, False])
    @mock.patch("os.path.realpath", side_effect=["walkroot",
                                                 "walkfile1",
                                                 "walkdir1"])
    @mock.patch("os.chown", side_effect=[True, True, True])
    @mock.patch("os.stat")
    def test_module_functions_backup_isdir(self, stat_mock, chown_mock, realpath_mock, islink_mock,
                                           walk_mock, copytree_mock, exists_mock, isdir_mock):
        stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0, st_dev=0, st_ino=0)
        walk_mock.return_value = (("walkroot", ("walkdir1",), ("walkfile1",)),)
        backed_files = {}
        self.assertEqual(ec2rlcore.prediag.backup("/test", backed_files, "/tmp"), "/tmp/test")
        self.assertEqual(backed_files, {"/test": "/tmp/test"})
        self.assertTrue(isdir_mock.called)
        self.assertTrue(exists_mock.called)
        self.assertTrue(copytree_mock.called)
        self.assertTrue(walk_mock.called)
        self.assertTrue(islink_mock.called)
        self.assertTrue(realpath_mock.called)
        self.assertTrue(chown_mock.called)
        self.assertTrue(stat_mock.called)

    @mock.patch("os.path.isdir", side_effect=[True, True])
    @mock.patch("os.path.exists", side_effect=[False, True])
    @mock.patch("shutil.copytree", side_effect=[True])
    @mock.patch("os.walk")
    @mock.patch("os.path.islink", side_effect=[True] * 4)
    @mock.patch("os.path.realpath", side_effect=["walkroot",
                                                 "walkfile1",
                                                 "walkfile2",
                                                 "walkdir1",
                                                 "walkdir2"])
    @mock.patch("os.chown", side_effect=[True] * 4)
    @mock.patch("os.stat")
    def test_module_functions_backup_isdir_skips(self, stat_mock, chown_mock, realpath_mock, islink_mock,
                                                 walk_mock, copytree_mock, exists_mock, isdir_mock):
        stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0, st_dev=0, st_ino=0)
        walk_mock.return_value = (("walkroot", ("walkdir1", "walkdir2",), ("walkfile1", "walkfile2")),)
        backed_files = {}
        with contextlib.redirect_stdout(StringIO()):
            self.assertEqual(ec2rlcore.prediag.backup("/test", backed_files, "/tmp"), "/tmp/test")
        self.assertEqual(backed_files, {"/test": "/tmp/test"})
        self.assertTrue(isdir_mock.called)
        self.assertTrue(exists_mock.called)
        self.assertTrue(copytree_mock.called)
        self.assertTrue(walk_mock.called)
        self.assertTrue(islink_mock.called)
        self.assertTrue(realpath_mock.called)
        self.assertTrue(chown_mock.called)
        self.assertTrue(stat_mock.called)

    @mock.patch("os.path.isdir", side_effect=[True, True])
    @mock.patch("os.path.exists", side_effect=[False, False])
    @mock.patch("os.makedirs", side_effect=[True])
    @mock.patch("shutil.copytree", side_effect=[True])
    @mock.patch("os.walk")
    @mock.patch("os.chown", side_effect=[True, True, True])
    @mock.patch("os.stat")
    def test_module_functions_backup_isdir_makedirs(self, stat_mock, chown_mock, walk_mock, copytree_mock,
                                                    makedirs_mock, exists_mock, isdir_mock):
        stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0)
        walk_mock.return_value = (("walkroot", ("walkdir",), ("walkfile1",)),)
        backed_files = {}
        self.assertEqual(ec2rlcore.prediag.backup("/test", backed_files, "/tmp"), "/tmp/test")
        self.assertEqual(backed_files, {"/test": "/tmp/test"})
        self.assertTrue(isdir_mock.called)
        self.assertTrue(exists_mock.called)
        self.assertTrue(makedirs_mock.called)
        self.assertTrue(copytree_mock.called)
        self.assertTrue(walk_mock.called)
        self.assertTrue(chown_mock.called)
        self.assertTrue(stat_mock.called)

    @mock.patch("os.path.isdir", side_effect=[False, False])
    @mock.patch("os.path.isfile", side_effect=[False])
    def test_module_functions_backup_not_file_or_dir(self, isfile_mock, isdir_mock):
        backed_files = {}
        with self.assertRaises(ec2rlcore.prediag.PrediagInvalidPathError):
            ec2rlcore.prediag.backup("test", backed_files, "/tmp"), "backed_path"
        self.assertTrue(isdir_mock.called)
        self.assertTrue(isfile_mock.called)

    def test_module_functions_backup_exists(self):
        """
        Test that the existing backup copy path is returned when trying to backup a file that
        has already been backed up.
        """
        backed_files = {"test": "backed_path"}
        self.assertEqual(ec2rlcore.prediag.backup("test", backed_files, "/tmp"), "backed_path")

    @mock.patch("os.path.exists", side_effect=[True])
    def test_module_functions_backup_destination_path_exists(self, exists_mock):
        """
        Test that an exception is raised when trying to backing up a file and the resulting backup location path
        is already an existing file/directory.
        """
        with self.assertRaises(ec2rlcore.prediag.PrediagDestinationPathExistsError) as ex:
            ec2rlcore.prediag.backup("test", dict(), "/tmp")
            self.assertEqual(ex, "Backup copy path already exists: /tmp/test")
        self.assertTrue(exists_mock.called)

    @mock.patch("os.path.exists", side_effect=[False])
    def test_module_functions_restore_invalid_path(self, os_exists_mock):
        backup_dict = {"test": "/tmp/test"}
        with self.assertRaises(ec2rlcore.prediag.PrediagInvalidPathError) as ex:
            ec2rlcore.prediag.restore(restoration_file_path="test", backed_files=backup_dict)
            self.assertEqual(ex, "Invalid path! Not a file or directory: /tmp/test")
        self.assertTrue(os_exists_mock.called)

    def test_module_functions_restore_not_in_dict(self):
        backup_dict = {"test": "/tmp/test"}
        self.assertFalse(ec2rlcore.prediag.restore(restoration_file_path="asdf", backed_files=backup_dict))

    @mock.patch("os.path.isdir", side_effect=[True])
    @mock.patch("shutil.copytree", side_effect=[True])
    @mock.patch("os.walk")
    @mock.patch("os.chown", side_effect=[True, True, True])
    @mock.patch("os.stat")
    def test_module_functions_restore_isdir(self, stat_mock, chown_mock, walk_mock, copytree_mock, isdir_mock):
        stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0)
        walk_mock.return_value = (("walkroot", ("walkdir",), ("walkfile1",)),)
        backup_dict = {"test": "/tmp/test"}
        self.assertTrue(ec2rlcore.prediag.restore(restoration_file_path="test", backed_files=backup_dict))
        self.assertTrue(isdir_mock.called)
        self.assertTrue(copytree_mock.called)
        self.assertTrue(walk_mock.called)
        self.assertTrue(chown_mock.called)
        self.assertTrue(stat_mock.called)

    @mock.patch("os.path.isdir", side_effect=[True])
    @mock.patch("shutil.copytree", side_effect=[True])
    @mock.patch("os.walk")
    @mock.patch("os.path.islink", side_effect=[True] * 4)
    @mock.patch("os.path.realpath", side_effect=["walkroot",
                                                 "walkfile1",
                                                 "walkfile2",
                                                 "walkdir1",
                                                 "walkdir2"])
    @mock.patch("os.chown", side_effect=[True] * 4)
    @mock.patch("os.stat")
    def test_module_functions_restore_isdir_skips(self, stat_mock, chown_mock, realpath_mock, islink_mock,
                                                  walk_mock, copytree_mock, isdir_mock):
        stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0, st_dev=0, st_ino=0)
        walk_mock.return_value = (("walkroot", ("walkdir1", "walkdir2",), ("walkfile1", "walkfile2")),)
        backup_dict = {"test": "/tmp/test"}
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(ec2rlcore.prediag.restore(restoration_file_path="test",
                                                      backed_files=backup_dict))
        self.assertTrue(isdir_mock.called)
        self.assertTrue(copytree_mock.called)
        self.assertTrue(walk_mock.called)
        self.assertTrue(islink_mock.called)
        self.assertTrue(realpath_mock.called)
        self.assertTrue(chown_mock.called)
        self.assertTrue(stat_mock.called)

    @mock.patch("os.path.exists", side_effect=[True])
    @mock.patch("os.path.isdir", side_effect=[False])
    @mock.patch("shutil.copy2", side_effect=[True])
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("os.stat")
    def test_module_functions_restore_isfile(self, stat_mock, chown_mock, copy2_mock, isdir_mock, exists_mock):
        stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0)
        backup_dict = {"test": "/tmp/test"}
        self.assertTrue(ec2rlcore.prediag.restore(restoration_file_path="test", backed_files=backup_dict))
        self.assertTrue(exists_mock.called)
        self.assertTrue(isdir_mock.called)
        self.assertTrue(copy2_mock.called)
        self.assertTrue(chown_mock.called)
        self.assertTrue(stat_mock.called)

    def test_module_functions__do_backup_restore_missing_source_path(self):
        """Test that an empty source_path string raises an exception. This arg should not be empty."""
        with contextlib.redirect_stdout(self.output):
            with self.assertRaises(ec2rlcore.prediag.PrediagArgumentError) as ex:
                ec2rlcore.prediag._do_backup_restore(source_path="",
                                                     source_path_is_dir=False,
                                                     destination_path="/tmp",
                                                     backed_files=dict())
                self.assertEqual(ex, "Missing or invalid args: source_path!")
                self.assertEqual(self.output.getvalue(), "Invalid source_path arg!")

    def test_module_functions__do_backup_restore_missing_is_dir(self):
        """Test that an empty is_dir string raises an exception. This arg should be a boolean."""
        with contextlib.redirect_stdout(self.output):
            with self.assertRaises(ec2rlcore.prediag.PrediagArgumentError) as ex:
                ec2rlcore.prediag._do_backup_restore(source_path="/something",
                                                     source_path_is_dir="",
                                                     destination_path="/tmp",
                                                     backed_files=dict())
                self.assertEqual(ex, "Missing or invalid args: is_dir!")
                self.assertEqual(self.output.getvalue(), "Invalid is_dir arg!")

    def test_module_functions__do_backup_restore_missing_destination_path(self):
        """Test that an empty destination_path string raises an exception. This arg should not be empty."""
        with contextlib.redirect_stdout(self.output):
            with self.assertRaises(ec2rlcore.prediag.PrediagArgumentError) as ex:
                ec2rlcore.prediag._do_backup_restore(source_path="/something",
                                                     source_path_is_dir=False,
                                                     destination_path="",
                                                     backed_files=dict())
                self.assertEqual(ex, "Missing or invalid args: destination_path!")
                self.assertEqual(self.output.getvalue(), "Invalid destination_path arg!")

    def test_module_functions__do_backup_restore_missing_backed_files(self):
        """Test that an missing backed_files arg raises an exception. This arg must be a dict."""
        with contextlib.redirect_stdout(self.output):
            with self.assertRaises(ec2rlcore.prediag.PrediagArgumentError) as ex:
                ec2rlcore.prediag._do_backup_restore(source_path="/something",
                                                     source_path_is_dir=False,
                                                     destination_path="/tmp",
                                                     backed_files=None)
                self.assertEqual(ex, "Missing or invalid args: backed_files!")
                self.assertEqual(self.output.getvalue(), "Invalid backed_files arg!")

    @mock.patch("ec2rlcore.prediag.check_root", return_value=True)
    @mock.patch("ec2rlcore.prediag.get_distro", return_value="LFS")
    @mock.patch("ec2rlcore.prediag.is_an_instance", return_value=False)
    def test_get_config_dict_all_unset(self, isaninstance_mock, get_distro_mock, check_root_mock):
        sys_config_dict = {"BACKED_FILES": {},
                           "BACKUP_DIR": "/var/tmp/ec2rl_test_module/backup",
                           "LOG_DIR": "/var/tmp/ec2rl_test_module",
                           "REMEDIATE": False,
                           "SUDO": True,
                           "DISTRO": "LFS",
                           "NOT_AN_INSTANCE": False}
        self.assertEqual(ec2rlcore.prediag.get_config_dict("test_module"), sys_config_dict)
        self.assertTrue(isaninstance_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)

    @mock.patch("ec2rlcore.prediag.check_root", return_value=True)
    @mock.patch("ec2rlcore.prediag.get_distro", return_value="LFS")
    @mock.patch("ec2rlcore.prediag.is_an_instance", return_value=False)
    @mock.patch.dict(os.environ, {"remediate": "True"})
    def test_get_config_dict_remediate_true(self, isaninstance_mock, get_distro_mock, check_root_mock):
        sys_config_dict = {"BACKED_FILES": {},
                           "BACKUP_DIR": "/var/tmp/ec2rl_test_module/backup",
                           "LOG_DIR": "/var/tmp/ec2rl_test_module",
                           "REMEDIATE": True,
                           "SUDO": True,
                           "DISTRO": "LFS",
                           "NOT_AN_INSTANCE": False}
        self.assertEqual(ec2rlcore.prediag.get_config_dict("test_module"), sys_config_dict)
        self.assertTrue(isaninstance_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)

    @mock.patch("ec2rlcore.prediag.check_root", return_value=True)
    @mock.patch("ec2rlcore.prediag.get_distro", return_value="LFS")
    @mock.patch("ec2rlcore.prediag.is_an_instance", return_value=False)
    @mock.patch.dict(os.environ, {"remediate": "False"})
    def test_get_config_dict_remediate_false(self, isaninstance_mock, get_distro_mock, check_root_mock):
        sys_config_dict = {"BACKED_FILES": {},
                           "BACKUP_DIR": "/var/tmp/ec2rl_test_module/backup",
                           "LOG_DIR": "/var/tmp/ec2rl_test_module",
                           "REMEDIATE": False,
                           "SUDO": True,
                           "DISTRO": "LFS",
                           "NOT_AN_INSTANCE": False}
        self.assertEqual(ec2rlcore.prediag.get_config_dict("test_module"), sys_config_dict)
        self.assertTrue(isaninstance_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)

    @mock.patch("ec2rlcore.prediag.check_root", return_value=True)
    @mock.patch("ec2rlcore.prediag.get_distro", return_value="LFS")
    @mock.patch("ec2rlcore.prediag.is_an_instance", return_value=False)
    @mock.patch.dict(os.environ, {"EC2RL_GATHEREDDIR": "/var/tmp/test/"})
    def test_get_config_dict_gathereddir_set(self, isaninstance_mock, get_distro_mock, check_root_mock):
        sys_config_dict = {"BACKED_FILES": {},
                           "BACKUP_DIR": "/var/tmp/test/test_module",
                           "LOG_DIR": "/var/tmp/ec2rl_test_module",
                           "REMEDIATE": False,
                           "SUDO": True,
                           "DISTRO": "LFS",
                           "NOT_AN_INSTANCE": False}
        self.assertEqual(ec2rlcore.prediag.get_config_dict("test_module"), sys_config_dict)
        self.assertTrue(isaninstance_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)

    @mock.patch("ec2rlcore.prediag.check_root", return_value=True)
    @mock.patch("ec2rlcore.prediag.get_distro", return_value="LFS")
    @mock.patch("ec2rlcore.prediag.is_an_instance", return_value=False)
    @mock.patch.dict(os.environ, {"EC2RL_LOGDIR": "/var/tmp/test/"})
    def test_get_config_dict_logdir_set(self, isaninstance_mock, get_distro_mock, check_root_mock):
        sys_config_dict = {"BACKED_FILES": {},
                           "BACKUP_DIR": "/var/tmp/ec2rl_test_module/backup",
                           "LOG_DIR": "/var/tmp/test/test_module",
                           "REMEDIATE": False,
                           "SUDO": True,
                           "DISTRO": "LFS",
                           "NOT_AN_INSTANCE": False}
        self.assertEqual(ec2rlcore.prediag.get_config_dict("test_module"), sys_config_dict)
        self.assertTrue(isaninstance_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)

    @mock.patch("ec2rlcore.prediag.check_root", return_value=True)
    @mock.patch("ec2rlcore.prediag.get_distro", return_value="LFS")
    @mock.patch.dict(os.environ, {"notaninstance": "True"})
    def test_get_config_dict_notaninstance_set_true(self, get_distro_mock, check_root_mock):
        sys_config_dict = {"BACKED_FILES": {},
                           "BACKUP_DIR": "/var/tmp/ec2rl_test_module/backup",
                           "LOG_DIR": "/var/tmp/ec2rl_test_module",
                           "REMEDIATE": False,
                           "SUDO": True,
                           "DISTRO": "LFS",
                           "NOT_AN_INSTANCE": True}
        self.assertEqual(ec2rlcore.prediag.get_config_dict("test_module"), sys_config_dict)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)

    @mock.patch("ec2rlcore.prediag.check_root", return_value=True)
    @mock.patch("ec2rlcore.prediag.get_distro", return_value="LFS")
    @mock.patch.dict(os.environ, {"notaninstance": "False"})
    def test_get_config_dict_notaninstance_set_false(self, get_distro_mock, check_root_mock):
        sys_config_dict = {"BACKED_FILES": {},
                           "BACKUP_DIR": "/var/tmp/ec2rl_test_module/backup",
                           "LOG_DIR": "/var/tmp/ec2rl_test_module",
                           "REMEDIATE": False,
                           "SUDO": True,
                           "DISTRO": "LFS",
                           "NOT_AN_INSTANCE": False}
        self.assertEqual(ec2rlcore.prediag.get_config_dict("test_module"), sys_config_dict)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)
