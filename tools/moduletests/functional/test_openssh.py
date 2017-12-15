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

"""Functional tests for "openssh" module."""

import os
import pwd
import shlex
import shutil
import stat
import subprocess
import sys
import unittest

import ec2rlcore.prediag
import moduletests.src.openssh


class TestSSH(unittest.TestCase):
    """SSH tests."""
    metadata_url = "http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key"
    command = [sys.executable, os.sep.join(["moduletests", "src", "openssh.py"])]
    env_dict = {"PATH": os.environ["PATH"],
                "EC2RL_CALLPATH": os.environ["EC2RL_CALLPATH"]}
    possible_users = ["ec2-user", "ubuntu"]
    uid = None
    username = None
    config_file_path = None
    backup_dir_path = "/var/tmp/ec2rl-functional"
    default_configuration_lines = ["HostKey /etc/ssh/ssh_host_rsa_key\n",
                                   "HostKey /etc/ssh/ssh_host_ecdsa_key\n",
                                   "HostKey /etc/ssh/ssh_host_ed25519_key\n",
                                   "SyslogFacility AUTHPRIV\n",
                                   "PermitRootLogin no\n",
                                   "AuthorizedKeysFile .ssh/authorized_keys\n",
                                   "PasswordAuthentication no\n",
                                   "ChallengeResponseAuthentication no\n",
                                   "UsePAM yes\n"]

    def __init__(self, *args, **kwargs):
        for username in self.possible_users:
            try:
                uid = pwd.getpwnam(username).pw_uid
                self.uid = uid
                self.username = username
                break
            except KeyError:
                pass
        if not self.username or not self.uid:
            raise Exception("Missing both the ec2-user user and the ubuntu user. One must be present for these tests.")

        self.config_file_path = moduletests.src.openssh.get_config_file_path()
        if not self.config_file_path:
            raise Exception("Failed to find the sshd configuration file.")

        if os.path.exists(self.backup_dir_path):
            shutil.rmtree(self.backup_dir_path)

        super(TestSSH, self).__init__(*args, **kwargs)

    def setUp(self):
        print("In test: {}".format(self._testMethodName))
        self.backed_files = dict()
        self.verified_fixed = False
        self.env_dict["remediate"] = "False"
        self.env_dict["notaninstance"] = "True"
        self.env_dict["inject_key"] = "False"
        self.env_dict["EC2RL_GATHEREDDIR"] = self.backup_dir_path
        os.makedirs(self.backup_dir_path, 0o700)

    def tearDown(self):
        self.backed_files = None
        del self.env_dict["remediate"]
        del self.env_dict["notaninstance"]
        del self.env_dict["inject_key"]
        shutil.rmtree(self.backup_dir_path)

    def test_ssh_missing_sshd(self):
        """Backup the sshd executable, remove it, verify the issue is detected, and restore the backup."""
        output_messages = list()
        output_messages.append("-- FAILURE     Missing sshd executable or it is not in $PATH: sshd")
        output_messages.append("-- Unable to check 20 items due to dependent check failures")
        sshd_path = ec2rlcore.prediag.which("sshd")

        ec2rlcore.prediag.backup(sshd_path, self.backed_files, self.backup_dir_path)
        try:
            os.remove(sshd_path)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            ec2rlcore.prediag.restore(sshd_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_etc_ssh_world_writable(self):
        """
        Set the permission mode of /etc/ssh to 777 (world writable), verify the issue is detected, and undo the
        permission mode change.
        """
        test_path = "/etc/ssh"
        output_messages = list()
        output_messages.append("-- FAILURE     Permission mode includes write for groups and/or other users: /etc/ssh")

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chmod(test_path, 0o755)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_etc_ssh_world_writable_remediate(self):
        """
        Set the permission mode of /etc/ssh to 777 (world writable), verify the issue is detected and remediated, and
        undo the permission mode change, if needed.
        """
        self.env_dict["remediate"] = "True"
        test_path = "/etc/ssh"
        output_messages = list()
        output_messages.append("-- FIXED       Permission mode includes write for groups and/or other users: /etc/ssh")

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_mode == (stat.S_IFDIR | 0o755):
                self.verified_fixed = True
        finally:
            os.chmod(test_path, 0o755)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_config_world_writable(self):
        """
        Set the permission mode of sshd_config to 777 (world writable), verify the issue is detected, and undo the
        permission mode change.
        """
        test_path = self.config_file_path
        output_messages = list()
        output_messages.append("-- FAILURE     Permission mode includes write for groups and/or other users: {}".format(
            test_path))

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chmod(test_path, 0o655)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_config_world_writable_remediate(self):
        """
        Set the permission mode of sshd_config to 777 (world writable), verify the issue is detected and remediated, and
        undo the permission mode change, if needed.
        """
        self.env_dict["remediate"] = "True"
        test_path = self.config_file_path
        output_messages = list()
        output_messages.append("-- FIXED       Permission mode includes write for groups and/or other users: {}".format(
            test_path))

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)

            if os.stat(test_path).st_mode == (stat.S_IFREG | 0o655):
                self.verified_fixed = True
        finally:
            os.chmod(test_path, 0o655)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_home_world_writable(self):
        """
        Set the permission mode of /home to 777 (world writable), verify the issue is detected, and undo the
        permission mode change.
        """
        test_path = "/home"
        output_messages = list()
        output_messages.append("-- FAILURE     Permission mode includes write for groups and/or other users: "
                               "/home")

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chmod(test_path, 0o755)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_home_world_writable_remediate(self):
        """
        Set the permission mode of sshd_config to 777 (world writable), verify the issue is detected and remediated, and
        undo the permission mode change, if needed.
        """
        test_path = "/home"
        self.env_dict["remediate"] = "True"
        output_messages = list()
        output_messages.append(
            "-- FIXED       Permission mode includes write for groups and/or other users: /home")

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_mode == (stat.S_IFDIR | 0o755):
                self.verified_fixed = True
        finally:
            os.chmod(test_path, 0o755)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_home_wrong_owner(self):
        """Set the uid of /home to 1337, verify the issue is detected, and undo the uid change."""
        test_path = "/home"
        output_messages = list()
        output_messages.append("FAILURE     Not owned by user root: /home")

        try:
            os.chown(test_path, 1337, -1)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chown(test_path, 0, -1)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_home_wrong_owner_remediate(self):
        """
        Set the uid of /home to 1337, verify the issue is detected and remediated, and undo the uid change, if needed.
        """
        self.env_dict["remediate"] = "True"
        test_path = "/home"
        output_messages = list()
        output_messages.append("-- FIXED       Not owned by user root: /home")

        try:
            os.chown(test_path, 1337, -1)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_uid == 0:
                self.verified_fixed = True
        finally:
            os.chown(test_path, 0, -1)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_user_home_world_writable(self):
        """
        Set the permission mode of a user's home directory (ec2-user or ubuntu) to 777 (world writable),
        verify the issue is detected, and undo the permission mode change.
        """
        test_path = "/home/{}".format(self.username)
        output_messages = list()
        output_messages.append("-- FAILURE     Permission mode includes write for groups and/or other users: {}".format(
            test_path))

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chmod(test_path, 0o755)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_user_home_world_writable_remediate(self):
        """
        Set the permission mode of user's home directory (ec2-user or ubuntu) to 777 (world writable),
        verify the issue is detected and remediated, and undo the permission mode change, if needed.
        """
        self.env_dict["remediate"] = "True"
        test_path = "/home/{}".format(self.username)
        output_messages = list()
        output_messages.append("-- FIXED       Permission mode includes write for groups and/or other users: {}".format(
            test_path))

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_mode == (stat.S_IFDIR | 0o755):
                self.verified_fixed = True
        finally:
            os.chmod(test_path, 0o755)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_user_home_wrong_owner(self):
        """Set the uid of user's home directory (ec2-user or ubuntu) to 0, verify the issue is detected,
        and undo the uid change."""
        test_path = "/home/{}".format(self.username)
        output_messages = list()
        output_messages.append("FAILURE     Not owned by user {}: {}".format(self.username, test_path))

        try:
            os.chown(test_path, 0, -1)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chown(test_path, self.uid, -1)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_user_home_wrong_owner_remediate(self):
        """
        Set the uid of user's home directory (ec2-user or ubuntu) to 0, verify the issue is detected and remediated,
        and undo the uid change, if needed.
        """
        self.env_dict["remediate"] = "True"
        test_path = "/home/{}".format(self.username)
        output_messages = list()
        output_messages.append("-- FIXED       Not owned by user {}: {}".format(self.username, test_path))

        try:
            os.chown(test_path, 0, -1)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_uid == self.uid:
                self.verified_fixed = True
        finally:
            os.chown(test_path, self.uid, -1)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_missing_auth_keys(self):
        """
        Rename a user's (ec2-user or ubuntu) authorized keys file , verify the issue is detected, and undo the rename.
        """
        output_messages = list()
        output_messages.append("-- FAILURE     Missing authorized key file")
        output_messages.append("-- Unable to check 2 items due to dependent check failures")
        moduletests.src.openssh.Problem.setup_config_vars()
        test_path = os.sep.join(["/home",
                                 self.username,
                                 moduletests.src.openssh.Problem.VARS_DICT["AUTH_KEYS"]["relative"][0]])

        ec2rlcore.prediag.backup(test_path, self.backed_files, self.backup_dir_path)
        try:
            os.remove(test_path)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            ec2rlcore.prediag.restore(test_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_missing_auth_keys_remediate(self):
        """
        Rename a user's (ec2-user or ubuntu) authorized keys file , verify the issue is detected and remediated,
        and undo the rename, if necesary.

        Note: this requires a new key to be specified or the environment to be an instance so the key can be pulled from
        the instance metadata. Without one of these, there is no way to know what key to add to the new authorized keys
        file. This test uses a key from the instance metadata and is, thus, only suitable to be run on an instance.
        """
        self.env_dict["remediate"] = "True"
        self.env_dict["notaninstance"] = "False"
        moduletests.src.openssh.Problem.setup_config_vars()
        test_path = os.sep.join(["/home",
                                 self.username,
                                 moduletests.src.openssh.Problem.VARS_DICT["AUTH_KEYS"]["relative"][0]])
        output_messages = list()
        output_messages.append("-- FIXED       Missing authorized key file")

        try:
            ec2rlcore.prediag.backup(test_path, self.backed_files, self.backup_dir_path)
            os.remove(test_path)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.path.isfile(test_path):
                self.verified_fixed = True
        finally:
            ec2rlcore.prediag.restore(test_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_auth_keys_wrong_owner(self):
        """
        Set the uid of user's (ec2-user or ubuntu) authorized keys file to 0, verify the issue is detected,
        and undo the uid change.
        """
        moduletests.src.openssh.Problem.setup_config_vars()
        test_path = os.sep.join(["/home",
                                 self.username,
                                 moduletests.src.openssh.Problem.VARS_DICT["AUTH_KEYS"]["relative"][0]])
        output_messages = list()
        output_messages.append("FAILURE     Not owned by user {}: {}".format(self.username, test_path))

        try:
            os.chown(test_path, 0, -1)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chown(test_path, self.uid, -1)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_auth_keys_wrong_owner_remediate(self):
        """
        Set the uid of user's (ec2-user or ubuntu) authorized keys file to 0, verify the issue is detected and
        remediated, and undo the uid change, if necesary.
        """
        self.env_dict["remediate"] = "True"
        moduletests.src.openssh.Problem.setup_config_vars()
        test_path = os.sep.join(["/home",
                                 self.username,
                                 moduletests.src.openssh.Problem.VARS_DICT["AUTH_KEYS"]["relative"][0]])
        output_messages = list()
        output_messages.append("-- FIXED       Not owned by user {}: {}".format(self.username, test_path))

        try:
            os.chown(test_path, 0, -1)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_uid == self.uid:
                self.verified_fixed = True
        finally:
            os.chown(test_path, self.uid, -1)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_auth_keys_world_writable(self):
        """
        Set the permission mode of a user's (ec2-user or ubuntu) authorized keys file to 777 (world writable),
        verify the issue is detected, and undo the permission mode change.
        """
        moduletests.src.openssh.Problem.setup_config_vars()
        test_path = os.sep.join(["/home",
                                 self.username,
                                 moduletests.src.openssh.Problem.VARS_DICT["AUTH_KEYS"]["relative"][0]])
        output_messages = list()
        output_messages.append("-- FAILURE     Permission mode includes write for groups and/or other users: {}".format(
            test_path))

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chmod(test_path, 0o655)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_auth_keys_world_writable_remediate(self):
        """
        Set the permission mode of a user's (ec2-user or ubuntu) authorized keys file to 777 (world writable),
        verify the issue is detected and remediated, and undo the permission mode change, if needed.
        """
        self.env_dict["remediate"] = "True"
        moduletests.src.openssh.Problem.setup_config_vars()
        test_path = os.sep.join(["/home",
                                 self.username,
                                 moduletests.src.openssh.Problem.VARS_DICT["AUTH_KEYS"]["relative"][0]])
        output_messages = list()
        output_messages.append("-- FIXED       Permission mode includes write for groups and/or other users: {}".format(
            test_path))

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_mode == (stat.S_IFREG | 0o655):
                self.verified_fixed = True
        finally:
            os.chmod(test_path, 0o655)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_config_bad_options(self):
        """
        Backup the sshd configuration file, write a new configuration file with a set of options including one
        invalid option, test that the problem is detected, and restore the backup configuration file copy.
        """
        test_path = self.config_file_path
        output_messages = list()
        output_messages.append("-- FAILURE     Bad lines in configuration file: {}".format(test_path))
        output_messages.append("-- Unable to check 18 items due to dependent check failures")
        bad_config_lines = ["bad option\n", "Port 22 # Good option \n", "# comment line\n"]

        ec2rlcore.prediag.backup(test_path, self.backed_files, self.backup_dir_path)
        try:
            with open(test_path, "w") as ssh_cfg_file:
                ssh_cfg_file.writelines(bad_config_lines)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            ec2rlcore.prediag.restore(test_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_config_bad_options_remediate(self):
        """
        Backup the sshd configuration file, write a new configuration file with a set of options including one
        invalid option, test that the problem is detected and remediated, and restore the backup configuration file
        copy.
        """
        self.env_dict["remediate"] = "True"
        test_path = self.config_file_path
        output_messages = list()
        output_messages.append("-- FIXED       Bad lines in configuration file: {}".format(test_path))
        bad_config_lines = ["bad option\n", "Port 22 # Good option \n", "# comment line\n"]
        fixed_config_lines = ["# bad option # commented out by ec2rl\n", "Port 22 # Good option \n", "# comment line\n"]

        ec2rlcore.prediag.backup(test_path, self.backed_files, self.backup_dir_path)
        try:
            with open(test_path, "w") as ssh_cfg_file:
                ssh_cfg_file.writelines(bad_config_lines)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)

            with open(test_path, "r") as ssh_cfg_file:
                if fixed_config_lines == ssh_cfg_file.readlines():
                    self.verified_fixed = True
        finally:
            ec2rlcore.prediag.restore(test_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_duplicate_authkey_lines(self):
        """
        Backup the sshd configuration file, write a new configuration file with multiple AuthorizedKeysFile lines,
        test that the problem is detected, and restore the backup configuration file copy.
        """
        test_path = self.config_file_path
        output_messages = list()
        output_messages.append(
            "-- FAILURE     sshd configuration file contains duplicate AuthorizedKeysFile lines: {}".format(test_path))
        output_messages.append("-- Unable to check 12 items due to dependent check failures")
        bad_config_lines = ["AuthorizedKeysFile	%h/.ssh/authorized_keys\n"
                            "AuthorizedKeysFile	.ssh/authorized_keys\n"
                            "AuthorizedKeysFile	/var/super/secret/location/authorized_keys\n"]
        ec2rlcore.prediag.backup(test_path, self.backed_files, self.backup_dir_path)
        try:
            with open(test_path, "w") as ssh_cfg_file:
                ssh_cfg_file.writelines(bad_config_lines)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            ec2rlcore.prediag.restore(test_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_duplicate_authkey_lines_remediate(self):
        """
        Backup the sshd configuration file, write a new configuration file with multiple AuthorizedKeysFile lines,
        test that the problem is detected and remediated, and restore the backup configuration file copy.
        """
        self.env_dict["remediate"] = "True"
        test_path = self.config_file_path
        output_messages = list()
        output_messages.append(
            "-- FIXED       sshd configuration file contains duplicate AuthorizedKeysFile lines: {}".format(test_path))
        bad_config_lines = ["AuthorizedKeysFile %h/.ssh/authorized_keys\n",
                            "AuthorizedKeysFile .ssh/authorized_keys\n",
                            "AuthorizedKeysFile /var/super/secret/location/authorized_keys\n"]
        fixed_config_lines = ["# AuthorizedKeysFile %h/.ssh/authorized_keys # commented out by ec2rl\n",
                              "# AuthorizedKeysFile .ssh/authorized_keys # commented out by ec2rl\n",
                              "# AuthorizedKeysFile /var/super/secret/location/authorized_keys # commented out by "
                              "ec2rl\n",
                              "AuthorizedKeysFile %h/.ssh/authorized_keys "
                              ".ssh/authorized_keys "
                              "/var/super/secret/location/authorized_keys\n"]

        ec2rlcore.prediag.backup(test_path, self.backed_files, self.backup_dir_path)
        try:
            with open(test_path, "w") as ssh_cfg_file:
                ssh_cfg_file.writelines(bad_config_lines)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)

            with open(test_path, "r") as ssh_cfg_file:
                if fixed_config_lines == ssh_cfg_file.readlines():
                    self.verified_fixed = True

        finally:
            ec2rlcore.prediag.restore(test_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_missing_priv_sep_dir(self):
        """
        Backup the user privilege separation directory, remove the user privilege separation directory, test that
        the problem is detected, and restore the backup user privilege separation directory copy.
        """
        test_path = moduletests.src.openssh.get_privilege_separation_dir()
        output_messages = list()
        output_messages.append("-- FAILURE     Missing privilege separation directory: {}".format(test_path))
        output_messages.append("-- Unable to check 4 items due to dependent check failures")

        ec2rlcore.prediag.backup(test_path, self.backed_files, self.backup_dir_path)
        try:
            shutil.rmtree(test_path)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            ec2rlcore.prediag.restore(test_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_missing_priv_sep_dir_remediate(self):
        """
        Backup the user privilege separation directory, remove the user privilege separation directory, test that
        the problem is detected and remediated, and restore the backup user privilege separation directory copy.
        """
        self.env_dict["remediate"] = "True"
        test_path = moduletests.src.openssh.get_privilege_separation_dir()
        output_messages = list()
        output_messages.append("-- FIXED       Missing privilege separation directory: {}".format(test_path))

        ec2rlcore.prediag.backup(test_path, self.backed_files, self.backup_dir_path)
        try:
            shutil.rmtree(test_path)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.path.isdir(test_path):
                self.verified_fixed = True
        finally:
            if os.path.exists(test_path):
                shutil.rmtree(test_path)
            ec2rlcore.prediag.restore(test_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_priv_sep_dir_wrong_owner(self):
        """
        Set the uid of the user privilege separation directory to 1337, verify the issue is detected, and
        undo the uid change.
        """
        test_path = moduletests.src.openssh.get_privilege_separation_dir()
        output_messages = list()
        output_messages.append("-- FAILURE     Not owned by user root: {}".format(test_path))

        try:
            os.chown(test_path, 1337, -1)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chown(test_path, 0, -1)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_priv_sep_dir_wrong_owner_remediate(self):
        """
        Set the uid of the user privilege separation directory to 1337, verify the issue is detected and remediated, and
        undo the uid change, if needed.
        """
        self.env_dict["remediate"] = "True"
        test_path = moduletests.src.openssh.get_privilege_separation_dir()
        output_messages = list()
        output_messages.append("-- FIXED       Not owned by user root: {}".format(test_path))

        try:
            os.chown(test_path, 1337, -1)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_uid == 0:
                self.verified_fixed = True
        finally:
            os.chown(test_path, 0, -1)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_priv_sep_dir_world_writable(self):
        """
        Set the permission mode of the user privilege separation user directory to 777 (world writable),
        verify the issue is detected, and undo the permission mode change.
        """
        test_path = moduletests.src.openssh.get_privilege_separation_dir()
        output_messages = list()
        output_messages.append(
            "-- FAILURE     Permission mode includes write for groups and/or other users: {}".format(test_path))

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.chmod(test_path, 0o700)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_priv_sep_dir_world_writable_remediate(self):
        """
        Set the permission mode of the user privilege separation user directory to 777 (world writable),
        verify the issue is detected and remediated, and undo the permission mode change, if needed.
        """
        self.env_dict["remediate"] = "True"
        test_path = moduletests.src.openssh.get_privilege_separation_dir()
        output_messages = list()
        output_messages.append("-- FIXED       Permission mode includes write for groups and/or other users: {}".format(
            test_path))

        try:
            os.chmod(test_path, 0o777)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_mode == (stat.S_IFDIR | 0o755):
                self.verified_fixed = True
        finally:
            os.chmod(test_path, 0o755)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_hostkeys_world_writable(self):
        """
        Create a test host key, backup the sshd configuration, modify the sshd configuration to include the new key,
        set the permission mode on key file to 777 (world writable), verify the issue is detected, and
        undo the sshd configuration change and remove the new host key file.
        """
        moduletests.src.openssh.Problem.setup_config_vars()
        test_path = "/root/test_key.dsa"
        output_messages = list()
        output_messages.append(
            "-- FAILURE     Permission mode includes permissions for groups and/or other users: {}".format(test_path))

        ec2rlcore.prediag.backup(self.config_file_path, self.backed_files, self.backup_dir_path)
        try:
            subprocess.check_call(
                shlex.split("ssh-keygen -q -t dsa -f {} -N \"\" -C \"\"".format(test_path)), stderr=subprocess.STDOUT)
            os.chmod(test_path, 0o777)
            with open(self.config_file_path, mode="w") as ssh_cfg_file:
                ssh_cfg_file.write("HostKey {}\n".format(test_path))
                ssh_cfg_file.flush()
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            os.remove(test_path)
            ec2rlcore.prediag.restore(self.config_file_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_hostkeys_world_writable_remediate(self):
        """
        Create a test host key, backup the sshd configuration, modify the sshd configuration to include the new key,
        set the permission mode on key file to 777 (world writable), verify the issue is detected and remediated, and
        undo the sshd configuration change and remove the new host key file.
        """
        self.env_dict["remediate"] = "True"
        moduletests.src.openssh.Problem.setup_config_vars()
        test_path = "/root/test_key.dsa"
        output_messages = list()
        output_messages.append(
            "-- FIXED       Permission mode includes permissions for groups and/or other users: {}".format(test_path))

        ec2rlcore.prediag.backup(self.config_file_path, self.backed_files, self.backup_dir_path)
        try:
            subprocess.check_call(
                shlex.split("ssh-keygen -q -t dsa -f {} -N \"\" -C \"\"".format(test_path)), stderr=subprocess.STDOUT)
            os.chmod(test_path, 0o777)
            with open(self.config_file_path, mode="w") as ssh_cfg_file:
                ssh_cfg_file.write("HostKey {}\n".format(test_path))
                ssh_cfg_file.flush()
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            if os.stat(test_path).st_mode == (stat.S_IFREG | 0o600):
                self.verified_fixed = True
        finally:
            os.remove(test_path)
            ec2rlcore.prediag.restore(self.config_file_path, self.backed_files)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    def test_ssh_missing_priv_sep_user(self):
        """
        Remove the privilege separation user, test that the issue is detected, and recreate the privilege separation
        user. There is no programatic way to obtain this user so the test will assume it is "sshd".
        """
        test_user = "sshd"
        test_path = moduletests.src.openssh.get_privilege_separation_dir()
        output_messages = list()
        output_messages.append("-- FAILURE     Missing privilege separation user: {}".format(test_user))

        try:
            with open(os.devnull) as devnull:
                subprocess.check_call(shlex.split("userdel sshd"), stderr=devnull)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            with open(os.devnull) as devnull:
                subprocess.check_call(shlex.split("useradd -s /sbin/nologin "
                                                  "-r -m "
                                                  "-c 'Privilege-separated SSH' "
                                                  "-d {} {}".format(test_path, test_user)),
                                      stdout=devnull,
                                      stderr=devnull)

        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_missing_priv_sep_user_remediate(self):
        """
        Remove the privilege separation user, test that the issue is detected and remediated, and recreate the
        privilege separation user, if needed. There is no programatic way to obtain this user so the test will
         assume it is "sshd".
        """
        self.env_dict["remediate"] = "True"
        # There is no programatic way to obtain this user so the test will assume it is "sshd".
        test_user = "sshd"
        test_path = moduletests.src.openssh.get_privilege_separation_dir()
        output_messages = list()
        output_messages.append("-- FIXED       Missing privilege separation user: {}".format(test_user))

        with open(os.devnull) as devnull:
            subprocess.check_call(shlex.split("userdel sshd"), stderr=devnull)

        try:
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            try:
                pwd.getpwnam(test_user)
                self.verified_fixed = True
            except KeyError:
                with open(os.devnull) as devnull:
                    subprocess.check_call(shlex.split("useradd -s /sbin/nologin "
                                                      "-r -m "
                                                      "-c 'Privilege-separated SSH' "
                                                      "-d {} {}".format(test_path, test_user)),
                                          stdout=devnull,
                                          stderr=devnull)
        except subprocess.CalledProcessError as cpe:
            with open(os.devnull) as devnull:
                subprocess.check_call(shlex.split("useradd -s /sbin/nologin "
                                                  "-r -m "
                                                  "-c 'Privilege-separated SSH' "
                                                  "-d {} {}".format(test_path, test_user)),
                                      stdout=devnull,
                                      stderr=devnull)
            process_output = cpe.stdout

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertTrue(self.verified_fixed)

    @unittest.skip("Does not work with distros that have GSSAPI patches applied.")
    def test_ssh_missing_hostkeys(self):
        """
        Backup the hostkeys, remove the host keys, test that the problem has been detected, and restore the backup
        host key copies.
        """
        output_messages = list()
        output_messages.append("-- FAILURE     Missing hostkey files")
        for key_file in ["/etc/ssh/ssh_host_dsa_key",
                         "/etc/ssh/ssh_host_ecdsa_key",
                         "/etc/ssh/ssh_host_ed25519_key",
                         "/etc/ssh/ssh_host_rsa_key"]:
            if os.path.exists(key_file):
                ec2rlcore.prediag.backup(key_file, self.backed_files, self.backup_dir_path)

        try:
            for key_file in self.backed_files:
                os.remove(key_file)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
        finally:
            for file in self.backed_files:
                ec2rlcore.prediag.restore(file, self.backed_files)
        for message in output_messages:
            self.assertTrue(message in process_output)

    @unittest.skip("Does not work with distros that have GSSAPI patches applied.")
    def test_ssh_missing_hostkeys_remediate(self):
        """
        Backup the hostkeys, remove the host keys, test that the problem has been detected and remediated, and
        restore the backup host key copies.
        """
        self.env_dict["remediate"] = "True"
        output_messages = list()
        output_messages.append("-- FIXED       Missing hostkey files")
        for key_file in ["/etc/ssh/ssh_host_dsa_key",
                         "/etc/ssh/ssh_host_ecdsa_key",
                         "/etc/ssh/ssh_host_ed25519_key",
                         "/etc/ssh/ssh_host_rsa_key"]:
            if os.path.exists(key_file):
                ec2rlcore.prediag.backup(key_file, self.backed_files, self.backup_dir_path)

        try:
            for key_file in self.backed_files:
                os.remove(key_file)
            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)
            for key_file in self.backed_files:
                self.assertTrue(os.path.isfile(key_file))
        finally:
            for key_file in self.backed_files:
                ec2rlcore.prediag.restore(key_file, self.backed_files)
        for message in output_messages:
            self.assertTrue(message in process_output)

    def test_ssh_chained_problems(self):
        """Create a set of problems on the system including problems dependent upon eachother, test that they are all
        detected and remediate, and restore all the backed up files.
        """
        moduletests.src.openssh.Problem.setup_config_vars()
        self.env_dict["remediate"] = "True"
        sshd_config_path = self.config_file_path
        auth_keys_path = os.sep.join(["/home",
                                      self.username,
                                      moduletests.src.openssh.Problem.VARS_DICT["AUTH_KEYS"]["relative"][0]])
        priv_sep_dir_path = moduletests.src.openssh.get_privilege_separation_dir()
        output_messages = list()
        output_messages.append("-- FIXED       Bad lines in configuration file: {}".format(sshd_config_path))
        output_messages.append("-- FIXED       Permission mode includes write for groups and/or other users: {}".format(
            auth_keys_path))
        output_messages.append("-- FIXED       Permission mode includes write for groups and/or other users: {}".format(
            priv_sep_dir_path))

        bad_config_lines = ["bad option\n", "Port 22 # Good option \n", "# comment line\n"]
        fixed_config_lines = ["# bad option # commented out by ec2rl\n", "Port 22 # Good option \n", "# comment line\n"]

        self.verified_fixed = list()

        ec2rlcore.prediag.backup(sshd_config_path, self.backed_files, self.backup_dir_path)
        try:
            with open(sshd_config_path, "w") as ssh_cfg_file:
                ssh_cfg_file.writelines(bad_config_lines)
            # In the DAG, the following two problems are addressed in vertices that are dependent upon
            # resolution of the config file problem
            os.chmod(auth_keys_path, 0o777)
            os.chmod(priv_sep_dir_path, 0o777)

            process_output = subprocess.check_output(TestSSH.command,
                                                     stderr=subprocess.STDOUT,
                                                     env=self.env_dict,
                                                     universal_newlines=True)

            with open(sshd_config_path, "r") as ssh_cfg_file:
                if fixed_config_lines == ssh_cfg_file.readlines():
                    self.verified_fixed.append(True)
                else:
                    self.verified_fixed.append(False)
            if os.stat(auth_keys_path).st_mode == (stat.S_IFREG | 0o655):
                self.verified_fixed.append(True)
            else:
                self.verified_fixed.append(False)
            if os.stat(priv_sep_dir_path).st_mode == (stat.S_IFDIR | 0o755):
                self.verified_fixed.append(True)
            else:
                self.verified_fixed.append(False)
        finally:
            ec2rlcore.prediag.restore(sshd_config_path, self.backed_files)
            os.chmod(auth_keys_path, 0o655)
            os.chmod(priv_sep_dir_path, 0o755)

        for message in output_messages:
            self.assertTrue(message in process_output)
        self.assertEqual(self.verified_fixed, [True] * 3)
