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
#
# Portions Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015 Python Software Foundation.
# All rights reserved.
# Please see LICENSE for applicable license terms and NOTICE for applicable notices.
# Details on all modifications are included within the comments.

"""
Prediagnostics module contains functions to be used to sanity check the OS and instance prior to running tests.

Functions:
    get_distro: determine the running Linux distribution
    check_root: verify whether the current user is root
    verify_metadata: verify the metadata server can be reached
    which: determine where in PATH a command is located
    get_net_driver: determine the network device driver for the first interface
    get_virt_type: determine the virtualization type of the running instance
    print_indent: a wrapper for print() that also takes a two-space indention level arg
    backup: creates a backup copy of a file or directory
    restore: restores a backup copy of a file or directory
    get_config_dict: create and return dictionary with all the necessary variables for module execution
Classes:
    None

Exceptions:
    None
"""
from __future__ import print_function
import os
import re
import shutil
import sys

try:
    import requests
except ImportError as ie:  # pragma: no cover
    print("ERROR:\tMissing Python module 'requests'.")
    print("\tPlease install this module and rerun ec2rl")
    sys.exit(1)


def get_distro():
    """
    Return the running Linux distribution.

    Returns:
        distro (str): the detected Linux distribution
    """

    distro = "unknown"
    alami_regex = re.compile(r"^Amazon Linux AMI release \d{4}\.\d{2}")
    alami2_regex = re.compile(r"^Amazon Linux (release \d \(Karoo\)|release \d.* \(\d{4}\.\d{2}\)|2)")
    rhel_regex = re.compile(r"^Red Hat Enterprise Linux Server release \d\.\d")

    # Amazon Linux & RHEL
    if os.path.isfile("/etc/system-release"):
        with open("/etc/system-release", "r") as fp:
            # This file is a single line
            distro_str = fp.readline()
            if re.match(alami_regex, distro_str):
                distro = "alami"
            elif re.match(alami2_regex, distro_str):
                distro = "alami2"
            elif re.match(rhel_regex, distro_str) or \
                    re.match(r"^CentOS.*release (\d+)\.(\d+)", distro_str):
                distro = "rhel"
            else:
                distro = "unknown for /etc/system-release"
    # SUSE
    # /etc/SuSE-release is deprecated
    elif os.path.isfile("/etc/SuSE-release"):
        with open("/etc/SuSE-release", "r") as fp:
            # This file is a single line
            distro_str = fp.readline()
            regex = re.compile(r"^SUSE Linux Enterprise Server \d{2}")
            if re.match(regex, distro_str):
                distro = "suse"
            else:
                distro = "unknown for /etc/SuSE-release"
    # Ubuntu
    elif os.path.isfile("/etc/lsb-release"):
        with open("/etc/lsb-release", "r") as fp:
            # This file is many lines in length
            lines = fp.readlines()
            distro = "unknown for /etc/lsb-release"
            for line in lines:
                if re.match(r"DISTRIB_ID=Ubuntu", line):
                    distro = "ubuntu"
                    break
    # Older Amazon Linux & RHEL
    elif os.path.isfile("/etc/issue"):
        with open("/etc/issue", "r") as fp:
            distro_str = fp.readline()
            if re.match(alami_regex, distro_str):
                distro = "alami"
            elif re.match(rhel_regex, distro_str) or re.match(r"^CentOS release \d\.\d+", distro_str):
                distro = "rhel"
            else:
                distro = "unknown for /etc/issue"
    # Amazon Linux & SUSE
    # /etc/os-release will be replacing /etc/SuSE-release in the future
    elif os.path.isfile("/etc/os-release"):
        with open("/etc/os-release", "r") as fp:
            lines = fp.readlines()
            distro = "unknown for /etc/os-release"
            for line in lines:
                if re.match(r"^PRETTY_NAME=\"SUSE Linux Enterprise Server \d{2}", line):
                    distro = "suse"
                    break
                elif re.match(r"^PRETTY_NAME=\"Amazon Linux AMI \d{4}\.\d{2}", line):
                    distro = "alami"
                    break
    return distro


def check_root():
    """Return whether the current user ID is 0 (root)."""
    return os.getegid() == 0


def verify_metadata():
    """Return whether the system can access the EC2 meta data and user data."""
    try:
        resp = requests.get("http://169.254.169.254/latest/meta-data/instance-id").status_code
        if resp == 200:
            return True
        elif resp == 401:
            token = (
                requests.put(
                    "http://169.254.169.254/latest/api/token",
                    headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
                    verify=False
                )
            ).text
            return requests.get("http://169.254.169.254/latest/meta-data/instance-id",
                                headers={'X-aws-ec2-metadata-token': token}).status_code == 200
        else:
            return False
    except requests.exceptions.ConnectionError:
        return False


def is_an_instance():
    """
    Return whether the running system is an EC2 instance based on criteria in AWS EC2 documentation.

    AWS EC2 documentation: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/identify_ec2_instances.html
    """
    sys_hypervisor_uuid = "/sys/hypervisor/uuid"
    try:
        if is_nitro():
            return True
        else:
            with open(sys_hypervisor_uuid) as uuid_file:
                if not uuid_file.readline().startswith("ec2"):
                    return False
            resp = requests.get(
                "http://169.254.169.254/latest/dynamic/instance-identity/document").status_code
            if resp == 200:
                return True
            elif resp == 401:
                token = (
                    requests.put(
                        "http://169.254.169.254/latest/api/token",
                        headers={
                            'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
                        verify=False
                    )
                ).text
                return requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document",
                                    headers={'X-aws-ec2-metadata-token': token}).status_code == 200
            else:
                return False
    except (IOError, OSError, requests.RequestException):
        # Python2: IOError
        # Python3: OSError -> FileNotFoundError
        return False


# This is shutil.which() from Python 3.5.2
# Replicating it here allows ec2rl to utilize which() in both python 2 & 3
def which(cmd, mode=os.F_OK | os.X_OK, path=None):  # pragma: no cover
    """
    Given a command, mode, and a PATH string, return the path which
    conforms to the given mode on the PATH, or None if there is no such
    file.

    `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
    of os.environ.get("PATH"), or can be overridden with a custom search
    path.
    """
    # Check that a given file can be accessed with the correct mode.
    # Additionally check that `file` is not a directory, as on Windows
    # directories pass the os.access check.
    def _access_check(fn, mode):
        return (os.path.exists(fn) and os.access(fn, mode)
                and not os.path.isdir(fn))

    # If we"re given a path with a directory part, look it up directly rather
    # than referring to PATH directories. This includes checking relative to the
    # current directory, e.g. ./script
    if os.path.dirname(cmd):
        if _access_check(cmd, mode):
            return cmd
        return None

    if path is None:
        path = os.environ.get("PATH", os.defpath)
    if not path:
        return None
    path = path.split(os.pathsep)

    if sys.platform == "win32":
        # The current directory takes precedence on Windows.
        if os.curdir not in path:
            path.insert(0, os.curdir)

        # PATHEXT is necessary to check on Windows.
        pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
        # See if the given file matches any of the expected path extensions.
        # This will allow us to short circuit when given "python.exe".
        # If it does match, only test that one, otherwise we have to try
        # others.
        if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
            files = [cmd]
        else:
            files = [cmd + ext for ext in pathext]
    else:
        # On other platforms you don't have things like PATHEXT to tell you
        # what file suffixes are executable, so just pass on cmd as-is.
        files = [cmd]

    seen = set()
    for directory in path:
        normdir = os.path.normcase(directory)
        if normdir not in seen:
            seen.add(normdir)
            for thefile in files:
                name = os.path.join(directory, thefile)
                if _access_check(name, mode):
                    return name
    return None


def get_net_driver():
    """
    Return the name of the driver for the first alphabetically ordered non-virtual network interface.

    Returns:
        driver_name (str): name of driver (e.g. ixgbevf)
    """
    try:
        net_device_list = list()
        # Add all non-virtual interfaces to the list and sort it
        for device in os.listdir("/sys/class/net"):
            if "virtual" not in os.path.abspath(os.readlink("/sys/class/net/{}".format(device))):
                net_device_list.append(device)
        if len(net_device_list) > 0:
            net_device_list = sorted(net_device_list)
            # readlink returns a path (e.g. ../../../../module/xen_netfront) so split the string
            # and return the last piece
            driver_name = os.readlink("/sys/class/net/{}/device/driver/module".format(net_device_list[0]))\
                .split("/")[-1]
        # Return an error if the list is somehow empty (didn't find any network devices)
        else:
            driver_name = "Unknown"
    # Catch OSError in Python2 and FileNotFoundError in Python3 (inherits from OSError)
    except OSError:
        driver_name = "Unknown"
    return driver_name


def get_virt_type():
    """
    Return the virtualization type as determined from the instance meta-data.

    Returns:
        profile (str): virtualization type (e.g. default-pv or devault-hvm)
    """

    try:
        # This path is only exposed on Nitro instance types.
        if is_nitro():
            profile = "nitro"
        else:
            profile_request = requests.get("http://169.254.169.254/latest/meta-data/profile")
            if profile_request.status_code == 200:
                profile = profile_request.text
            elif profile_request.status_code == 401:
                token=(
                    requests.put(
                        "http://169.254.169.254/latest/api/token", 
                        headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'}, 
                        verify=False
                    )
                ).text
                profile = requests.get(
                    "http://169.254.169.254/latest/meta-data/profile", 
                    headers={'X-aws-ec2-metadata-token': token}
                ).text
            else:
                profile = "ERROR"
    except requests.exceptions.ConnectionError:
        raise PrediagConnectionError("Failed to connect to AWS EC2 metadata service.")
    return profile

def is_nitro():
    """
    Returns if the virtualization type is nitro as determined by /sys/devices/virtual/dmi/id/board_asset_tag.
    Also returns true for bare metal instances as well, due to being part of the
    nitro ecosystem, even though they technically do not have the nitro hypervisor.
    """
    try:
        nitro_asset = "/sys/devices/virtual/dmi/id/board_asset_tag"
        with open(nitro_asset) as asset_file:
            if asset_file.readline().startswith("i-"):
                return True
            else:
                return False
    except (IOError, OSError):
        # Python2: IOError
        # Python3: OSError -> FileNotFoundError
        return False

def print_indent(str_arg, level=0):
    """Print str_arg indented two spaces per level."""
    print("{}{}".format(level * "  ", str_arg))


def backup(path_to_backup, backed_files, backup_dir):
    """
    Given a path, file_path, copy it to backup_dir, update the backed_files dict, and return the path of the new
    backup copy. If the path has already been backed up then return the existing backup path and exit immediately
    without copying.

    PrediagTargetPathExistsError is raised if the backup destination for a directory already exists. This check is a
    pre-screen for shutil.copytreee which raises FileExistsError if the destination path exists.

    This function is intended for use within Python-based remediation modules.

    Parameters:
        path_to_backup (str): path to the file to back up
        backed_files (dict): original path of backed up files (keys) and
        the path to the backup copy of the file (values)
        backup_dir (str): path to the directory containing backup file copies

    Returns:
        backup_location_path (str): path to the backup copy of the file
    """
    # If a backup copy of the file already exists, do not perform another, redundant backup operation.
    if path_to_backup in backed_files:
        return backed_files[path_to_backup]

    backup_location_path = "".join([backup_dir, path_to_backup])
    if os.path.exists(backup_location_path):
        raise PrediagDestinationPathExistsError(backup_location_path)

    if os.path.isdir(path_to_backup):
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, mode=0o0700)

        _do_backup_restore(source_path=path_to_backup,
                           source_path_is_dir=True,
                           destination_path=backup_location_path,
                           backed_files=backed_files)
    elif os.path.isfile(path_to_backup):
        backup_location_parent_path = "".join([backup_dir, os.path.dirname(path_to_backup)])
        if not os.path.exists(backup_location_parent_path):
            os.makedirs(backup_location_parent_path, mode=0o0700)

        _do_backup_restore(source_path=path_to_backup,
                           source_path_is_dir=False,
                           destination_path=backup_location_path,
                           backed_files=backed_files)
    else:
        raise PrediagInvalidPathError(path_to_backup)

    backed_files[path_to_backup] = backup_location_path

    return backup_location_path


def restore(restoration_file_path, backed_files):
    """
    Given a path a file to restore, restoration_file_path, lookup the location of the backup copy, and
    copy the file to location.

    This function is intended for use within Python-based remediation modules.

    Parameters:
        restoration_file_path (str): path to the file backup to be restored
        backed_files (dict): names of backed up files (keys) and the path to the backup copy of the file (values)

    Returns:
        (bool): whether the operation was successful
    """
    if restoration_file_path not in backed_files:
        return False
    backup_copy_path = backed_files[restoration_file_path]
    if not os.path.exists(backup_copy_path):
        raise PrediagInvalidPathError(backup_copy_path)

    _do_backup_restore(source_path=backup_copy_path,
                       source_path_is_dir=os.path.isdir(backup_copy_path),
                       destination_path=restoration_file_path,
                       backed_files=backed_files)
    return True


def _do_backup_restore(source_path, source_path_is_dir, destination_path, backed_files):
    """
    Given a path a file to restore, source_path, lookup the location of the backup copy in the backup dict,
    backed files, and copy the file to restoration location, destination_path. A regular file at destination_path
    will be overwritten. shutil.copytree will not copy over an existing directory at destination_path and
    FileExistsError will be raised.

    Parameters:
        source_path (str): file path to be copied
        source_path_is_dir (bool): whether source_path is a directory
        destination_path (str): where source_path should be copied to
        backed_files (dict): names of backed up files (keys) and the path to the backup copy of the file (values)

    Returns:
        True (bool): if the operation was successful
    """
    args_valid = True
    bad_args = list()
    if not source_path:
        print("Invalid source_path arg!")
        args_valid = False
        bad_args.append("souce_path")
    if not isinstance(source_path_is_dir, bool):
        print("Invalid source_path_is_dir arg!")
        args_valid = False
        bad_args.append("source_path_is_dir")
    if not destination_path:
        print("Invalid destination_path arg!")
        args_valid = False
        bad_args.append("destination_path")
    if not isinstance(backed_files, dict):
        print("Invalid backed_files arg!")
        args_valid = False
        bad_args.append("backed_files")
    if not args_valid:
        raise PrediagArgumentError(bad_args)

    if source_path_is_dir:
        shutil.copytree(source_path, destination_path)
        seen_paths = set()
        for root, dirs, files in os.walk(destination_path, followlinks=True):
            # Check if this root has already been visited (avoids symlink-induced infinite looping)
            realroot = os.path.realpath(root)
            os.chown(realroot, os.stat(source_path).st_uid, os.stat(source_path).st_gid)
            seen_paths.add(realroot)

            for file_name in files:
                full_file_path = os.path.join(realroot, file_name)
                real_file_path = os.path.realpath(full_file_path)
                this_path_key = "{}{}".format(str(os.stat(real_file_path).st_dev), str(os.stat(real_file_path).st_ino))
                if this_path_key in seen_paths and os.path.islink(full_file_path):
                    print_indent("Skipping previously seen symlink target: {} -> {}".format(full_file_path,
                                                                                            real_file_path),
                                 level=1)
                    continue
                else:
                    seen_paths.add(this_path_key)

                original_stat = os.stat(os.path.join(source_path, file_name))
                os.chown(full_file_path, original_stat.st_uid, original_stat.st_gid)
            for dir_name in dirs:
                full_dir_path = os.path.join(realroot, dir_name)
                real_dir_path = os.path.realpath(full_dir_path)
                this_path_key = "{}{}".format(str(os.stat(real_dir_path).st_dev), str(os.stat(real_dir_path).st_ino))
                if this_path_key in seen_paths and os.path.islink(full_dir_path):
                    print_indent("Skipping previously seen symlink target: {} -> {}".format(full_dir_path,
                                                                                            real_dir_path),
                                 level=1)
                    continue
                else:
                    seen_paths.add(this_path_key)

                original_stat = os.stat(os.path.join(source_path, dir_name))
                os.chown(full_dir_path, original_stat.st_uid, original_stat.st_gid)
        return True
    else:
        shutil.copy2(source_path, destination_path)
        os.chown(destination_path, os.stat(source_path).st_uid, os.stat(source_path).st_gid)
        return True


def get_config_dict(module_name):
    """
    Create and return dictionary with all the necessary variables for module execution.

    BACKUP_DIR: directory containing file backups. When run via ec2rl, this is a subdirectory inside LOG_DIR.
    LOG_DIR: directory containing ec2rl logs else a default location if not running through ec2rl.
    BACKED_FILES: dict containing "original file path":"back up file copy path" key:pair values.
    REMEDIATE: controls whether remediation is to be attempted. The default is to only perform detection.
    SUDO: whether the module is being executed as root/with sudo privileges.
    DISTRO: the detected distribution of Linux running on the system.
    NOT_AN_INSTANCE: True if running on anything but an EC2 instance.

    Parameters:
        module_name (str): name of the module requesting the configuration dict.

    Returns:
        sys_config_dict (dict): variable name and variable value pairs usable inside Python ec2rl modules.
    """
    sys_config_dict = {"BACKUP_DIR": "/var/tmp/ec2rl_{}/backup".format(module_name),
                       "LOG_DIR": "/var/tmp/ec2rl_{}".format(module_name),
                       "BACKED_FILES": dict(),
                       "REMEDIATE": False,
                       "SUDO": check_root(),
                       "NOT_AN_INSTANCE": False}
    try:
        sys_config_dict["DISTRO"] = os.environ["EC2RL_DISTRO"]
    except KeyError:
        sys_config_dict["DISTRO"] = get_distro()

    try:
        if os.environ["notaninstance"] == "True":
            sys_config_dict["NOT_AN_INSTANCE"] = True
    except KeyError:
        sys_config_dict["NOT_AN_INSTANCE"] = is_an_instance()

    try:
        if os.environ["remediate"] == "True":
            sys_config_dict["REMEDIATE"] = True
    except KeyError:
        # Keep default of False
        pass

    try:
        sys_config_dict["BACKUP_DIR"] = os.path.join(os.environ["EC2RL_GATHEREDDIR"], module_name)
    except KeyError:
        # Keep default
        pass
    try:
        sys_config_dict["LOG_DIR"] = os.path.join(os.environ["EC2RL_LOGDIR"], module_name)
    except KeyError:
        # Keep default
        pass

    return sys_config_dict


class PrediagError(Exception):
    """Base class for exceptions in this module."""
    pass


class PrediagConnectionError(PrediagError):
    """A Requests ConnectionError occurred."""
    def __init__(self, error_message, *args):
        message = "Connection error: {}".format(error_message)
        super(PrediagConnectionError, self).__init__(message, *args)


class PrediagArgumentError(PrediagError):
    """One or more arguments were missing or invalid."""
    def __init__(self, arg_list, *args):
        message = "Missing or invalid args: {}!".format(", ".join(arg_list))
        super(PrediagArgumentError, self).__init__(message, *args)


class PrediagDestinationPathExistsError(PrediagError):
    """Destination destination directory already exists."""
    def __init__(self, path_str, *args):
        message = "Backup copy path already exists: {}".format(path_str)
        super(PrediagDestinationPathExistsError, self).__init__(message, *args)


class PrediagInvalidPathError(PrediagError):
    """The given path is not a file or directory."""
    def __init__(self, path_str, *args):
        message = "Invalid path. Not a file or directory: {}".format(path_str)
        super(PrediagInvalidPathError, self).__init__(message, *args)
