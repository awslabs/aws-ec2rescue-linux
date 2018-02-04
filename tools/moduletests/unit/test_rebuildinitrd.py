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
Unit tests for the rebuildinitrd module
"""
import os
import subprocess
import sys
import unittest

import mock

import moduletests.src.rebuildinitrd

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


class Testrebuildinitrd(unittest.TestCase):

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("os.listdir", return_value="initramfs-4.9.32-15.41.amzn1.x86_64.img")
    def test_getboot(self, listdir_mock):
        self.assertEqual(moduletests.src.rebuildinitrd.getboot(), "initramfs-4.9.32-15.41.amzn1.x86_64.img")

    @mock.patch("moduletests.src.rebuildinitrd.open",  mock.mock_open(read_data="/boot"))
    @mock.patch("subprocess.check_output", return_value=b"stuff")
    def test_mountboot(self, check_output_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.mountboot())

    @mock.patch("moduletests.src.rebuildinitrd.open",  mock.mock_open(read_data=""))
    def test_mountboot_emptyfstab(self):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.mountboot()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.rebuildinitrd.open",  side_effect=Exception)
    def test_mountboot_exception(self, open_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.mountboot()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.rebuildinitrd.getboot", return_value=["initramfs-4.9.32-15.41.amzn1.x86_64.img", "garbage"])
    def test_getinitrd(self, getboot_mock):
        self.assertEqual(moduletests.src.rebuildinitrd.getinitrd(), ["initramfs-4.9.32-15.41.amzn1.x86_64.img"])

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initramfs-4.9.32-15.41.amzn1.x86_64.img"])
    @mock.patch("shutil.copyfile", return_value=True)
    @mock.patch("subprocess.check_output", return_value=b"stuff")
    def test_rebuildalami(self, getinitrd_mock, copyfile_mock, check_output_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.rebuildalami())

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initramfs-4.9.32-15.41.amzn1.x86_64.img"])
    @mock.patch("shutil.copyfile", side_effect=Exception)
    def test_rebuildalami_copyfail(self, getinitrd_mock, copyfile_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.rebuildalami()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initramfs-4.9.32-15.41.amzn1.x86_64.img"])
    @mock.patch("shutil.copyfile", return_value=True)
    @mock.patch("subprocess.check_output", side_effect=Exception)
    def test_rebuildalami_rebuildfail(self, getinitrd_mock, copyfile_mock, check_output_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.rebuildalami()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initrd.img-4.4.0-1031-aws"])
    @mock.patch("shutil.copyfile", return_value=True)
    @mock.patch("subprocess.check_output", return_value=b"stuff")
    def test_rebuildubuntu(self, getinitrd_mock, copyfile_mock, check_output_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.rebuildubuntu())

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initrd.img-4.4.0-1031-aws"])
    @mock.patch("shutil.copyfile", side_effect=Exception)
    def test_rebuildubuntu_copyfail(self, getinitrd_mock, copyfile_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.rebuildubuntu()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initrd.img-4.4.0-1031-aws"])
    @mock.patch("shutil.copyfile", return_value=True)
    @mock.patch("subprocess.check_output", side_effect=Exception)
    def test_rebuildubuntu_rebuildfail(self, getinitrd_mock, copyfile_mock, check_output_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.rebuildubuntu()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initramfs-3.10.0-514.el7.x86_64.img"])
    @mock.patch("shutil.copyfile", return_value=True)
    @mock.patch("subprocess.check_output", return_value=b"stuff")
    def test_rebuildrhel(self, getinitrd_mock, copyfile_mock, check_output_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.rebuildrhel())

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initramfs-3.10.0-514.el7.x86_64.img"])
    @mock.patch("shutil.copyfile", side_effect=Exception)
    def test_rebuildrhel_copyfail(self, getinitrd_mock, copyfile_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.rebuildrhel()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initramfs-3.10.0-514.el7.x86_64.img"])
    @mock.patch("shutil.copyfile", return_value=True)
    @mock.patch("subprocess.check_output", side_effect=Exception)
    def test_rebuildrhel_rebuildfail(self, getinitrd_mock, copyfile_mock, check_output_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.rebuildrhel()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initrd-4.4.21-69-default"])
    @mock.patch("shutil.copyfile", return_value=True)
    @mock.patch("subprocess.check_output", return_value=b"stuff")
    def test_rebuildsuse(self, getinitrd_mock, copyfile_mock, check_output_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.rebuildsuse())

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initrd-4.4.21-69-default"])
    @mock.patch("shutil.copyfile", side_effect=Exception)
    def test_rebuildsuse_copyfail(self, getinitrd_mock, copyfile_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.rebuildsuse()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch("moduletests.src.rebuildinitrd.getinitrd", return_value=["initrd-4.4.21-69-default"])
    @mock.patch("shutil.copyfile", return_value=True)
    @mock.patch("subprocess.check_output", side_effect=Exception)
    def test_rebuildsuse_rebuildfail(self, getinitrd_mock, copyfile_mock, check_output_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.rebuildsuse()
        self.assertEqual(ex.exception.code, 0)

    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "alami"})
    @mock.patch("moduletests.src.rebuildinitrd.getboot", return_value=False)
    @mock.patch("moduletests.src.rebuildinitrd.mountboot", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuildalami", return_value=True)
    def test_run_mount_alami(self, getboot_mock, mountboot_mock, rebuildalami_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.run())

    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "alami"})
    @mock.patch("moduletests.src.rebuildinitrd.getboot", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuildalami", return_value=True)
    def test_run_nomount_alami(self, getboot_mock, rebuildalami_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.run())

    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "ubuntu"})
    @mock.patch("moduletests.src.rebuildinitrd.getboot", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuildubuntu", return_value=True)
    def test_run_nomount_ubuntu(self, getboot_mock, rebuildalami_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.run())

    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "rhel"})
    @mock.patch("moduletests.src.rebuildinitrd.getboot", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuildrhel", return_value=True)
    def test_run_nomount_rhel(self, getboot_mock, rebuildalami_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.run())

    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "suse"})
    @mock.patch("moduletests.src.rebuildinitrd.getboot", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuildsuse", return_value=True)
    def test_run_nomount_suse(self, getboot_mock, rebuildalami_mock):
        self.assertTrue(moduletests.src.rebuildinitrd.run())

    @mock.patch.dict(os.environ, {"EC2RL_DISTRO": "alami"})
    @mock.patch("moduletests.src.rebuildinitrd.getboot", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuildalami", side_effect=Exception)
    def test_run_nomount_alami_exception(self, getboot_mock, rebuildalami_mock):
        with self.assertRaises(SystemExit) as ex:
            moduletests.src.rebuildinitrd.run()
        self.assertEqual(ex.exception.code, 0)
