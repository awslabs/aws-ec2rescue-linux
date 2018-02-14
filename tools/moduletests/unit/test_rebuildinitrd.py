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


class Testrebuildinitrd(unittest.TestCase):

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @mock.patch("moduletests.src.rebuildinitrd.open",  mock.mock_open(read_data="/boot"))
    @mock.patch("subprocess.check_output", return_value="stuff")
    def test_mount_boot(self, check_output_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.mount_boot())
        self.assertTrue(check_output_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.open",  mock.mock_open(read_data=""))
    def test_mount_boot_emptyfstab(self):
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.rebuildinitrd.mount_boot())
        self.assertEqual(self.output.getvalue(), "[WARN] No /boot in /etc/fstab and /boot empty. Cannot proceed\n")

    @mock.patch("moduletests.src.rebuildinitrd.open",  side_effect=IOError("test"))
    def test_mount_boot_exception(self, open_mock):
        with contextlib.redirect_stdout(self.output):
            with self.assertRaises(IOError) as ex:
                moduletests.src.rebuildinitrd.mount_boot()
        self.assertEqual(self.output.getvalue(), "[WARN] /boot empty. Cannot proceed.\n")
        self.assertEqual(str(ex.exception), "test")
        self.assertTrue(open_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.os.listdir",
                return_value=["initramfs-4.9.32-15.41.amzn1.x86_64.img", "garbage"])
    def test_get_initrd(self, os_listdir_mock):
        self.assertEqual(moduletests.src.rebuildinitrd.get_initrd(), ["initramfs-4.9.32-15.41.amzn1.x86_64.img"])
        self.assertTrue(os_listdir_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.os.listdir",
                return_value=["garbage"])
    def test_get_initrd_empty(self, os_listdir_mock):
        with self.assertRaises(ValueError) as ve:
            moduletests.src.rebuildinitrd.get_initrd()
        self.assertEqual(str(ve.exception), "initrd list is empty! Did not find any initrd files!")
        self.assertTrue(os_listdir_mock.called)

    def test_rebuild_invalid_distro(self):
        with self.assertRaises(ValueError) as assert_obj:
            moduletests.src.rebuildinitrd.rebuild("invalid", dict(), "/test/path")
        self.assertEqual(str(assert_obj.exception), "[FAILURE] unsupported distribution: invalid")

    @mock.patch("moduletests.src.rebuildinitrd.get_initrd", return_value=["initramfs-4.9.76-3.78.amzn1.x86_64.img",
                                                                          "initramfs-4.9.77-31.58.amzn1.x86_64.img"])
    @mock.patch("moduletests.src.rebuildinitrd.backup", return_value=True)
    @mock.patch("subprocess.check_output", return_value="stuff")
    def test_rebuild_alami_success(self, check_output_mock, backup_mock, get_initrd_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.rebuild("alami", dict(), "/test/path"))
        self.assertTrue(self.output.getvalue().endswith("Creating new initial ramdisk for 4.9.77-31.58.amzn1.x86_64\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(get_initrd_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_initrd", return_value=["initramfs-4.9.76-3.78.amzn2.x86_64.img",
                                                                          "initramfs-4.9.77-31.58.amzn2.x86_64.img"])
    @mock.patch("moduletests.src.rebuildinitrd.backup", return_value=True)
    @mock.patch("subprocess.check_output", return_value="stuff")
    def test_rebuild_alami2_success(self, check_output_mock, backup_mock, get_initrd_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.rebuild("alami2", dict(), "/test/path"))
        self.assertTrue(self.output.getvalue().endswith("Creating new initial ramdisk for 4.9.77-31.58.amzn2.x86_64\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(get_initrd_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_initrd", return_value=["initramfs-3.10.0-514.el7.x86_64.img"])
    @mock.patch("moduletests.src.rebuildinitrd.backup", return_value=True)
    @mock.patch("subprocess.check_output", return_value="stuff")
    def test_rebuild_rhel_success(self, check_output_mock, backup_mock, get_initrd_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.rebuild("rhel", dict(), "/test/path"))
        self.assertTrue(self.output.getvalue().endswith("Creating new initial ramdisk for 3.10.0-514.el7.x86_64\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(get_initrd_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_initrd", return_value=["initrd.img-4.4.0-1031-aws"])
    @mock.patch("moduletests.src.rebuildinitrd.backup", return_value=True)
    @mock.patch("subprocess.check_output", return_value="stuff")
    def test_rebuild_ubuntu_success(self, check_output_mock, backup_mock, get_initrd_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.rebuild("ubuntu", dict(), "/test/path"))
        self.assertTrue(self.output.getvalue().endswith("Creating new initial ramdisk for 4.4.0-1031-aws\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(get_initrd_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_initrd", return_value=["initrd-4.4.59-92.17-default"])
    @mock.patch("moduletests.src.rebuildinitrd.backup", return_value=True)
    @mock.patch("subprocess.check_output", return_value="stuff")
    def test_rebuild_suse_success(self, check_output_mock, backup_mock, get_initrd_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.rebuild("suse", dict(), "/test/path"))
        self.assertTrue(self.output.getvalue().endswith("Creating new initial ramdisk for 4.4.59-92.17-default\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(get_initrd_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_initrd", return_value=[])
    def test_rebuild_alami_get_initrd_failure(self, get_initrd_mock):
        with self.assertRaises(Exception) as assert_obj:
            moduletests.src.rebuildinitrd.rebuild("alami", dict(), "/test/path")
        self.assertEqual(str(assert_obj.exception), "[FAILURE] Failed to find initial ramdisk!")
        self.assertTrue(get_initrd_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_initrd", return_value=["initramfs-4.9.32-15.41.amzn1.x86_64.img"])
    @mock.patch("moduletests.src.rebuildinitrd.backup", side_effect=IOError)
    def test_rebuild_alami_backup_failure(self, backup_mock, get_initrd_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(Exception, moduletests.src.rebuildinitrd.rebuild, "alami", dict(), "/test/path")
        self.assertTrue(self.output.getvalue().endswith("[WARN] Backup of initial ramdisk failed.\n"))
        self.assertTrue(backup_mock.called)
        self.assertTrue(get_initrd_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_initrd", return_value=["initramfs-4.9.32-15.41.amzn1.x86_64.img"])
    @mock.patch("moduletests.src.rebuildinitrd.backup", return_value=True)
    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "call"))
    def test_rebuild_alami_subprocess_failure(self, check_output_mock, backup_mock, get_initrd_mock):
        with contextlib.redirect_stdout(self.output):
            self.assertRaises(subprocess.CalledProcessError,
                              moduletests.src.rebuildinitrd.rebuild, "alami", dict(), "/test/path")
        self.assertTrue(self.output.getvalue().endswith("[WARN] Rebuild of initial ramdisk failed.\n"))
        self.assertTrue(check_output_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(get_initrd_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_config_dict")
    @mock.patch("moduletests.src.rebuildinitrd.os.listdir", return_value=False)
    @mock.patch("moduletests.src.rebuildinitrd.mount_boot", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuild", return_value=True)
    def test_run_mount_alami(self, rebuild_mock, mount_boot_mock, os_listdir_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True,
                                    "DISTRO": "alami"}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.run())
        self.assertTrue("[SUCCESS] initial ramdisk rebuilt" in self.output.getvalue())
        self.assertTrue(rebuild_mock.called)
        self.assertTrue(mount_boot_mock.called)
        self.assertTrue(os_listdir_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_config_dict")
    @mock.patch("moduletests.src.rebuildinitrd.os.listdir", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuild", return_value=True)
    def test_run_nomount_alami(self, rebuild_mock, os_listdir_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True,
                                    "DISTRO": "alami"}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.run())
        self.assertTrue("[SUCCESS] initial ramdisk rebuilt" in self.output.getvalue())
        self.assertTrue(rebuild_mock.called)
        self.assertTrue(os_listdir_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_config_dict")
    @mock.patch("moduletests.src.rebuildinitrd.os.listdir", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuild", return_value=True)
    def test_run_nomount_ubuntu(self, rebuild_mock, os_listdir_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True,
                                    "DISTRO": "ubuntu"}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.run())
        self.assertTrue("[SUCCESS] initial ramdisk rebuilt" in self.output.getvalue())
        self.assertTrue(rebuild_mock.called)
        self.assertTrue(os_listdir_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_config_dict")
    @mock.patch("moduletests.src.rebuildinitrd.os.listdir", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuild", return_value=True)
    def test_run_nomount_rhel(self, rebuild_mock, os_listdir_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True,
                                    "DISTRO": "rhel"}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.run())
        self.assertTrue("[SUCCESS] initial ramdisk rebuilt" in self.output.getvalue())
        self.assertTrue(rebuild_mock.called)
        self.assertTrue(os_listdir_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_config_dict")
    @mock.patch("moduletests.src.rebuildinitrd.os.listdir", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuild", return_value=True)
    def test_run_nomount_suse(self, rebuild_mock, os_listdir_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True,
                                    "DISTRO": "suse"}
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(moduletests.src.rebuildinitrd.run())
        self.assertTrue("[SUCCESS] initial ramdisk rebuilt" in self.output.getvalue())
        self.assertTrue(rebuild_mock.called)
        self.assertTrue(os_listdir_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_config_dict")
    @mock.patch("moduletests.src.rebuildinitrd.os.listdir", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuild", side_effect=IOError("test"))
    def test_run_nomount_alami_exception(self, rebuild_mock, os_listdir_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": dict(),
                                    "REMEDIATE": True,
                                    "SUDO": True,
                                    "DISTRO": "alami"}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.rebuildinitrd.run())
        self.assertTrue("/boot has contents\ntest\n"
                        "[WARN] module generated an exception and exited abnormally. "
                        "Review the logs to determine the cause of the issue.\n"
                        in self.output.getvalue())
        self.assertTrue(rebuild_mock.called)
        self.assertTrue(os_listdir_mock.called)
        self.assertTrue(config_mock.called)

    @mock.patch("moduletests.src.rebuildinitrd.get_config_dict")
    @mock.patch("moduletests.src.rebuildinitrd.os.listdir", return_value=True)
    @mock.patch("moduletests.src.rebuildinitrd.rebuild", side_effect=IOError("test"))
    @mock.patch("moduletests.src.rebuildinitrd.restore", return_value=True)
    def test_run_nomount_alami_exception_restore(self, restore_mock, rebuild_mock, os_listdir_mock, config_mock):
        config_mock.return_value = {"BACKUP_DIR": "/var/tmp/ec2rl",
                                    "LOG_DIR": "/var/tmp/ec2rl",
                                    "BACKED_FILES": {"some file": "test"},
                                    "REMEDIATE": True,
                                    "SUDO": True,
                                    "DISTRO": "alami"}
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(moduletests.src.rebuildinitrd.run())
        self.assertTrue("/boot has contents\ntest\n"
                        "[WARN] module generated an exception and exited abnormally. "
                        "Review the logs to determine the cause of the issue.\n"
                        in self.output.getvalue())
        self.assertTrue(restore_mock.called)
        self.assertTrue(rebuild_mock.called)
        self.assertTrue(os_listdir_mock.called)
        self.assertTrue(config_mock.called)
