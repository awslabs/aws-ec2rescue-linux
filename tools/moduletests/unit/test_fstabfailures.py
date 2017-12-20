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
Unit tests for the fstabfailures module
"""
import os
import subprocess
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

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(read_data="LABEL=/     /           ext4    "
                                                                   "defaults,noatime,nofail  0   0\n"))
    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "alami"})
    def test_alami_defaultfstab(self):
        self.assertTrue(moduletests.src.fstabfailures.defaultfstab())

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(read_data="LABEL=/     /           ext4    "
                                                                    "defaults,noatime,nofail  0   0\n"))
    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "suse"})
    def test_suse_defaultfstab(self):
        self.assertTrue(moduletests.src.fstabfailures.defaultfstab())


    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(read_data="LABEL=/     /           ext4    "
                                                                   "defaults,noatime,nofail  0   0\n"))
    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "rhel"})
    def test_rhel_defaultfstab(self):
        self.assertTrue(moduletests.src.fstabfailures.defaultfstab())

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(read_data="LABEL=/     /           ext4    "
                                                                   "defaults,noatime,nofail  0   0\n"))
    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "ubuntu"})
    def test_ubuntu_defaultfstab(self):
        self.assertTrue(moduletests.src.fstabfailures.defaultfstab())

    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(read_data="LABEL=/     /           ext4    "
                                                                   "defaults,noatime,nofail  0   0\n"))
    def test_nodistro_defaultfstab(self):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.fstabfailures.defaultfstab()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.fstabfailures.open", side_effect=Exception)
    def test_exception_defaultfstab(self, open_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.fstabfailures.defaultfstab()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.fstabfailures.defaultfstab", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.os.path.isfile", return_value=False)
    def test_nofstab_fstabexists(self, defaultfstab_mock, isfile_mock):
        self.assertTrue(moduletests.src.fstabfailures.checkfstabexists())

    @mock.patch("moduletests.src.fstabfailures.defaultfstab", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.os.path.isfile", return_value=True)
    def test_fstab_fstabexists(self, defaultfstab_mock, isfile_mock):
        self.assertTrue(moduletests.src.fstabfailures.checkfstabexists())

    def test_full_parsefstab(self):
        open_mock = mock.mock_open(read_data="LABEL=/ / ext4 defaults,noatime,nofail 0 0\n")
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
            self.assertEqual(moduletests.src.fstabfailures.parsefstab(), [{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
                'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '0'}])

    def test_5entry_parsefstab(self):
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
            self.assertEqual(moduletests.src.fstabfailures.parsefstab(), [{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
                'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '0'}])

    def test_4entry_parsefstab(self):
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
            self.assertEqual(moduletests.src.fstabfailures.parsefstab(), [{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
                'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '0'}])

    def test_comment_parsefstab(self):
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
            self.assertEqual(moduletests.src.fstabfailures.parsefstab(), [])

    @mock.patch("moduletests.src.fstabfailures.defaultfstab", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.backupfstab", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.open", side_effect=Exception)
    def test_exception_parsefstab(self, defaultfstab_mock, backupfstab_mock, open_mock):
        self.assertTrue(moduletests.src.fstabfailures.parsefstab())

    @mock.patch("moduletests.src.fstabfailures.shutil.copyfile", return_value=True)
    def test_success_backupfstab(self, copyfile_mock):
        self.assertTrue(moduletests.src.fstabfailures.backupfstab())

    @mock.patch("moduletests.src.fstabfailures.shutil.copyfile", side_effect=Exception)
    def test_exception_backupfstab(self, open_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.fstabfailures.backupfstab()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.fstabfailures.parsefstab", return_value=[{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
        'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '0'}])
    def test_nofsck_checkfsck(self, parsefstab_mock):
        fstab = moduletests.src.fstabfailures.parsefstab()
        self.assertFalse(moduletests.src.fstabfailures.checkfsck(fstab))

    @mock.patch("moduletests.src.fstabfailures.parsefstab", return_value=[{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
        'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '1'}])
    def test_nofsck_checkfsck(self, parsefstab_mock):
        fstab = moduletests.src.fstabfailures.parsefstab()
        self.assertTrue(moduletests.src.fstabfailures.checkfsck(fstab))

    @mock.patch("moduletests.src.fstabfailures.parsefstab", return_value=[{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
        'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '0'}])
    def test_nofail_checknofail(self, parsefstab_mock):
        fstab = moduletests.src.fstabfailures.parsefstab()
        self.assertFalse(moduletests.src.fstabfailures.checknofail(fstab))


    @mock.patch("moduletests.src.fstabfailures.parsefstab", return_value=[{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
        'ext4', 'Options': 'defaults,noatime', 'Dump': '0', 'fsck': '0'}])
    def test_fail_checknofail(self, parsefstab_mock):
        fstab = moduletests.src.fstabfailures.parsefstab()
        self.assertTrue(moduletests.src.fstabfailures.checknofail(fstab))

    @mock.patch("moduletests.src.fstabfailures.parsefstab", return_value=[{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
        'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '0'}])
    @mock.patch("moduletests.src.fstabfailures.open", mock.mock_open(read_data="stuff"))
    def test_success_rewritefstab(self, parsefstab_mock):
        fstab = moduletests.src.fstabfailures.parsefstab()
        self.assertTrue(moduletests.src.fstabfailures.rewritefstab(fstab))

    @mock.patch("moduletests.src.fstabfailures.parsefstab", return_value=[{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
        'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '0'}])
    @mock.patch("moduletests.src.fstabfailures.open", side_effect=Exception)
    def test_exception_rewritefstab(self, parsefstab_mock, open_mock):
        fstab = moduletests.src.fstabfailures.parsefstab()
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.fstabfailures.rewritefstab(fstab)
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.fstabfailures.checkfstabexists", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.parsefstab", return_value=[{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
        'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '0'}])
    @mock.patch("moduletests.src.fstabfailures.backupfstab", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.rewritefstab", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.checknofail", return_value=True)
    def test_rewrite_run(self, checkfstabexists_mock, parsefstab_mock, backupfstab_mock, rewritefstab_mock,
                         checknofail_mock):
        self.assertTrue(moduletests.src.fstabfailures.run())

    @mock.patch("moduletests.src.fstabfailures.checkfstabexists", return_value=True)
    @mock.patch("moduletests.src.fstabfailures.parsefstab", return_value=[{'Filesystem': 'LABEL=/', 'Mountpoint': '/', 'FSType':
        'ext4', 'Options': 'defaults,noatime,nofail', 'Dump': '0', 'fsck': '0'}])
    def test_norewrite_run(self, checkfstabexists_mock, parsefstab_mock):
        self.assertTrue(moduletests.src.fstabfailures.run())

    @mock.patch("moduletests.src.fstabfailures.checkfstabexists", side_effect=Exception)
    def test_exception_run(self, checkfstabexists_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.fstabfailures.run()
        self.assertEqual(ex.exception.code, 0)