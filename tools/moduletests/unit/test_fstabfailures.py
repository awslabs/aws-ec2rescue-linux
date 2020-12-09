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
Unit tests for the fstabfailures module
"""
import sys
import unittest

import mock

import moduletests.src.fstabfailures

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


class Testfstabfailures(unittest.TestCase):
    config_file_path = "/etc/fstab"

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(
        read_data="LABEL=/ / ext4 defaults,noatime,nofail 0 0\n"))
    def test_alami_defaultfstab(self):
        self.assertTrue(moduletests.src.fstabfailures.write_default_fstab(self.config_file_path, "alami"))

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(
        read_data="LABEL=/ / xfs defaults,noatime,nofail 0 0\n"))
    def test_alami2_defaultfstab(self):
        self.assertTrue(moduletests.src.fstabfailures.write_default_fstab(self.config_file_path, "alami2"))

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(
        read_data="LABEL=/ / ext4 defaults,noatime,nofail 0 0\n"))
    def test_suse_defaultfstab(self):
        self.assertTrue(moduletests.src.fstabfailures.write_default_fstab(self.config_file_path, "suse"))

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(
        read_data="LABEL=/ / ext4 defaults,noatime,nofail 0 0\n"))
    def test_rhel_defaultfstab(self):
        self.assertTrue(moduletests.src.fstabfailures.write_default_fstab(self.config_file_path, "rhel"))

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(
        read_data="LABEL=/ / ext4 defaults,noatime,nofail 0 0\n"))
    def test_ubuntu_defaultfstab(self):
        self.assertTrue(moduletests.src.fstabfailures.write_default_fstab(self.config_file_path, "ubuntu"))

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(
        read_data="LABEL=/ / ext4 defaults,noatime,nofail 0 0\n"))
    def test_nodistro_defaultfstab(self):
        with self.assertRaises(ValueError) as ve:
            moduletests.src.fstabfailures.write_default_fstab(self.config_file_path, "invalid distro string")
            self.assertEqual(str(ve), "Invalid distribution. Unable to continue.")

    @mock.patch("moduletests.src.fstabfailures.open", side_effect=IOError)
    def test_exception_defaultfstab(self, open_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(IOError, moduletests.src.fstabfailures.write_default_fstab,
                              self.config_file_path,
                              "alami")
        self.assertEqual(self.output.getvalue(), "[WARN] Unable to write default /etc/fstab, aborting.\n")
        self.assertTrue(open_mock.called)

    def test_full_parse_fstab_with_blank_lines(self):
        open_mock = mock.mock_open(read_data="LABEL=/ / ext4 defaults,noatime,nofail 0 0\n \n\t\n")

        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)
        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("moduletests.src.fstabfailures.open", open_mock):
            with contextlib.redirect_stdout(self.output):
                self.assertEqual(moduletests.src.fstabfailures.parse_fstab(self.config_file_path),
                                 [{"Filesystem": "LABEL=/",
                                   "Mountpoint": "/",
                                   "FSType": "ext4",
                                   "Options": "defaults,noatime,nofail",
                                   "Dump": "0", "fsck": "0"}])

    def test_parse_fstab_five_entry(self):
        open_mock = mock.mock_open(read_data="LABEL=/ / ext4 defaults,noatime,nofail 0\n")

        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)
        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("moduletests.src.fstabfailures.open", open_mock):
            with contextlib.redirect_stdout(self.output):
                self.assertEqual(moduletests.src.fstabfailures.parse_fstab(self.config_file_path),
                                 [{"Filesystem": "LABEL=/",
                                   "Mountpoint": "/",
                                   "FSType": "ext4",
                                   "Options": "defaults,noatime,nofail",
                                   "Dump": "0", "fsck": "0"}])

    def test_parse_fstab_four_entry(self):
        open_mock = mock.mock_open(read_data="LABEL=/ / ext4 defaults,noatime,nofail\n")

        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)
        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("moduletests.src.fstabfailures.open", open_mock):
            with contextlib.redirect_stdout(self.output):
                self.assertEqual(moduletests.src.fstabfailures.parse_fstab(self.config_file_path),
                                 [{"Filesystem": "LABEL=/",
                                   "Mountpoint": "/",
                                   "FSType": "ext4",
                                   "Options": "defaults,noatime,nofail",
                                   "Dump": "0", "fsck": "0"}])

    def test_comment_parse_fstab(self):
        open_mock = mock.mock_open(read_data="#\n")

        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)
        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("moduletests.src.fstabfailures.open", open_mock):
            self.assertEqual(moduletests.src.fstabfailures.parse_fstab(self.config_file_path), [])

    @mock.patch("moduletests.src.fstabfailures.open", side_effect=IOError)
    def test_exception_parse_fstab(self, open_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(IOError, moduletests.src.fstabfailures.parse_fstab, self.config_file_path)
        self.assertEqual(self.output.getvalue(), "Unable to open and parse /etc/fstab. Invalid fstab?\n")
        self.assertTrue(open_mock.called)

    def test_nofsck_check_fsck_true(self):
        fstab = [{"Filesystem": "LABEL=/",
                  "Mountpoint": "/",
                  "FSType": "ext4",
                  "Options": "defaults,noatime,nofail",
                  "Dump": "0", "fsck": "1"}]
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.fstabfailures.check_fsck(fstab))
        self.assertEqual(self.output.getvalue(), "Checking for volumes with fsck enabled\n\tfsck enabled: 'LABEL=/'\n")

    def test_nofsck_check_fsck_false(self):
        fstab = [{"Filesystem": "LABEL=/",
                  "Mountpoint": "/",
                  "FSType": "ext4",
                  "Options": "defaults,noatime,nofail",
                  "Dump": "0", "fsck": "0"}]
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.fstabfailures.check_fsck(fstab))
        self.assertEqual(self.output.getvalue(), "Checking for volumes with fsck enabled\n")

    def test_nofail_check_nofail_true(self):
        fstab = [{"Filesystem": "LABEL=/",
                  "Mountpoint": "/",
                  "FSType": "ext4",
                  "Options": "defaults,noatime",
                  "Dump": "0", "fsck": "0"}]
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.fstabfailures.check_nofail(fstab))
        self.assertEqual(self.output.getvalue(), "Checking for volumes without nofail\n\tMissing nofail: 'LABEL=/'\n")

    def test_nofail_check_nofail_false(self):
        fstab = [{"Filesystem": "LABEL=/",
                  "Mountpoint": "/",
                  "FSType": "ext4",
                  "Options": "defaults,noatime,nofail",
                  "Dump": "0", "fsck": "0"}]
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.fstabfailures.check_nofail(fstab))
        self.assertEqual(self.output.getvalue(), "Checking for volumes without nofail\n")

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(read_data="stuff"))
    def test_success_fix(self):
        fstab = [{"Filesystem": "LABEL=/",
                  "Mountpoint": "/",
                  "FSType": "ext4",
                  "Options": "defaults,noatime,nofail",
                  "Dump": "0", "fsck": "0"}]
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.fstabfailures.fix(fstab, self.config_file_path))
        self.assertTrue(self.output.getvalue().endswith("aster/docs/modules/fstabfailures.md for further details\n"))

    @mock.patch("moduletests.src.fstabfailures.open", side_effect=IOError)
    def test_exception_fix(self, open_mock):
        with contextlib.redirect_stdout(self.output):
            fstab = [{"Filesystem": "LABEL=/",
                      "Mountpoint": "/",
                      "FSType": "ext4",
                      "Options": "defaults,noatime,nofail",
                      "Dump": "0", "fsck": "0"}]
            self.assertRaises(IOError, moduletests.src.fstabfailures.fix, fstab, self.config_file_path)
        self.assertEqual(self.output.getvalue(), "[WARN] Unable to write new /etc/fstab. "
                                                 "Please review logs to determine the cause of the issue.\n")
        self.assertTrue(open_mock.called)

    @mock.patch("moduletests.src.fstabfailures.get_config_dict")
    @mock.patch("moduletests.src.fstabfailures.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.backup", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.parse_fstab", return_value=[{"Filesystem": "LABEL=/",
                                                                            "Mountpoint": "/",
                                                                            "FSType": "ext4",
                                                                            "Options": "defaults,noatime,nofail",
                                                                            "Dump": "0", "fsck": "0"}])
    @mock.patch("moduletests.src.fstabfailures.check_nofail", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.check_fsck", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.fix", return_value=True)
    def test_run_rewrite(self,
                         fix_mock,
                         check_fsck_mock,
                         check_nofail_mock,
                         parse_fstab,
                         backup_mock,
                         isfile_mock,
                         get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": dict(),
                                             "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.fstabfailures.run())
        self.assertEqual(self.output.getvalue(), "/etc/fstab found, continuing.\n")
        self.assertTrue(check_fsck_mock.called)
        self.assertTrue(check_nofail_mock.called)
        self.assertTrue(fix_mock.called)
        self.assertTrue(parse_fstab.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.fstabfailures.get_config_dict")
    @mock.patch("moduletests.src.fstabfailures.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.backup", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.parse_fstab", return_value=[{"Filesystem": "LABEL=/",
                                                                            "Mountpoint": "/",
                                                                            "FSType": "ext4",
                                                                            "Options": "defaults,noatime,nofail",
                                                                            "Dump": "0", "fsck": "0"}])
    @mock.patch("moduletests.src.fstabfailures.check_nofail", return_value=False)
    @mock.patch("moduletests.src.fstabfailures.check_fsck", return_value=False)
    def test_run_norewrite(self,
                           check_fsck_mock,
                           check_nofail_mock,
                           parse_fstab_mock,
                           backup_mock,
                           isfile_mock,
                           get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": dict(),
                                             "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.fstabfailures.run())
        self.assertTrue(self.output.getvalue().endswith(
            "[SUCCESS] /etc/fstab has nofail set and is not set to fsck.\n"))
        self.assertTrue(check_fsck_mock.called)
        self.assertTrue(check_nofail_mock.called)
        self.assertTrue(parse_fstab_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.fstabfailures.get_config_dict")
    @mock.patch("moduletests.src.fstabfailures.os.path.isfile", return_value=False)
    @mock.patch("moduletests.src.fstabfailures.write_default_fstab", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.backup", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.parse_fstab", return_value=[{"Filesystem": "LABEL=/",
                                                                            "Mountpoint": "/",
                                                                            "FSType": "ext4",
                                                                            "Options": "defaults,noatime,nofail",
                                                                            "Dump": "0", "fsck": "0"}])
    @mock.patch("moduletests.src.fstabfailures.check_nofail", return_value=False)
    @mock.patch("moduletests.src.fstabfailures.check_fsck", return_value=False)
    def test_run_default_fstab_norewrite(self,
                                         check_fsck_mock,
                                         check_nofail_mock,
                                         parse_fstab_mock,
                                         backup_mock,
                                         write_default_fstab_mock,
                                         isfile_mock,
                                         get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": dict(),
                                             "REMEDIATE": True,
                                             "DISTRO": "alami"}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.fstabfailures.run())
        self.assertTrue(self.output.getvalue().endswith(
            "[SUCCESS] /etc/fstab has nofail set and is not set to fsck.\n"))
        self.assertTrue(check_fsck_mock.called)
        self.assertTrue(check_nofail_mock.called)
        self.assertTrue(parse_fstab_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(write_default_fstab_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.fstabfailures.get_config_dict")
    @mock.patch("moduletests.src.fstabfailures.os.path.isfile", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.backup", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.parse_fstab", side_effect=[OSError,
                                                                          [{"Filesystem": "LABEL=/",
                                                                            "Mountpoint": "/",
                                                                            "FSType": "ext4",
                                                                            "Options": "defaults,noatime,nofail",
                                                                            "Dump": "0", "fsck": "0"}]])
    @mock.patch("moduletests.src.fstabfailures.write_default_fstab", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.check_nofail", return_value=False)
    @mock.patch("moduletests.src.fstabfailures.check_fsck", return_value=False)
    def test_run_parse_exception(self,
                                 check_fsck_mock,
                                 check_nofail_mock,
                                 write_default_fstab_mock,
                                 parse_fstab_mock,
                                 backup_mock,
                                 isfile_mock,
                                 get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": dict(),
                                             "REMEDIATE": True,
                                             "DISTRO": "alami"}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.fstabfailures.run())
        self.assertTrue(self.output.getvalue().endswith(
            "[SUCCESS] /etc/fstab has nofail set and is not set to fsck.\n"))
        self.assertTrue(check_fsck_mock.called)
        self.assertTrue(check_nofail_mock.called)
        self.assertTrue(write_default_fstab_mock.called)
        self.assertTrue(parse_fstab_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(isfile_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    @mock.patch("moduletests.src.fstabfailures.get_config_dict")
    @mock.patch("moduletests.src.fstabfailures.os.path.isfile", side_effect=Exception)
    @mock.patch("moduletests.src.fstabfailures.restore")
    def test_run_exception(self, restore_mock, isfile_mock, get_config_dict_mock):
        get_config_dict_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                             "LOG_DIR": "/var/tmp/ec2rl",
                                             "BACKED_FILES": {self.config_file_path: "/some/path"},
                                             "REMEDIATE": True}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.fstabfailures.run())
        self.assertTrue(self.output.getvalue().endswith("Review the logs to determine the cause of the issue.\n"))
        self.assertTrue(restore_mock.called)
        self.assertTrue(isfile_mock.called)

    @mock.patch("moduletests.src.fstabfailures.get_config_dict", side_effect=Exception)
    def test_run_config_exception(self, get_config_dict_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.fstabfailures.run())
        self.assertTrue(self.output.getvalue().endswith("Review the logs to determine the cause of the issue.\n"))
        self.assertTrue(get_config_dict_mock.called)
