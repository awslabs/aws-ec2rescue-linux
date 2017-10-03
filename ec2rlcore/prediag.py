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

Classes:
    None

Exceptions:
    None
"""
from __future__ import print_function
import os
import re
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
        distro (string): the detected Linux distribution
    """

    distro = "unknown"

    # Amazon Linux & RHEL
    if os.path.isfile("/etc/system-release"):
        with open("/etc/system-release", "r") as fp:
            # This file is a single line
            distro_str = fp.readline()
            alami_regex = re.compile(r"^Amazon Linux AMI release [0-9]{4}\.[0-9]{2}")
            rhel_regex = re.compile(r"^Red Hat Enterprise Linux Server release [0-9]\.[0-9]")
            centos_regex = re.compile(r"^CentOS Linux release ([0-9])\.([0-9])\.([0-9]{4})")
            if re.match(alami_regex, distro_str):
                distro = "alami"
            elif re.match(rhel_regex, distro_str) or re.match(centos_regex, distro_str):
                distro = "rhel"
            else:
                distro = "unknown for /etc/system-release"
    # SUSE
    # /etc/SuSE-release is deprecated
    elif os.path.isfile("/etc/SuSE-release"):
        with open("/etc/SuSE-release", "r") as fp:
            # This file is a single line
            distro_str = fp.readline()
            regex = re.compile(r"^SUSE Linux Enterprise Server [0-9]{2}")
            if re.match(regex, distro_str):
                distro = "suse"
            else:
                distro = "unknown for /etc/SuSE-release"
    # Ubuntu
    elif os.path.isfile("/etc/lsb-release"):
        with open("/etc/lsb-release", "r") as fp:
            # This file is many lines in length
            lines = fp.readlines()
            regex = re.compile(r"DISTRIB_ID=Ubuntu")
            for line in lines:
                if re.match(regex, line):
                    distro = "ubuntu"
                    break
                else:
                    distro = "unknown for /etc/lsb-release"
    # Older Amazon Linux & RHEL
    elif os.path.isfile("/etc/issue"):
        with open("/etc/issue", "r") as fp:
            distro_str = fp.readline()
            alami_regex = re.compile(r"^Amazon Linux AMI release [0-9]{4}\.[0-9]{2}")
            rhel_regex = re.compile(r"^Red Hat Enterprise Linux Server release \d\.\d+")
            centos_regex = re.compile(r"^CentOS release \d\.\d+")
            if re.match(alami_regex, distro_str):
                distro = "alami"
            elif re.match(rhel_regex, distro_str) or re.match(centos_regex, distro_str):
                distro = "rhel"
            else:
                distro = "unknown for /etc/issue"
    # Amazon Linux & SUSE
    # /etc/os-release will be replacing /etc/SuSE-release in the future
    elif os.path.isfile("/etc/os-release"):
        with open("/etc/os-release", "r") as fp:
            lines = fp.readlines()
            for line in lines:
                if re.match(r"^PRETTY_NAME=\"SUSE Linux Enterprise Server [0-9]{2}", line):
                    distro = "suse"
                    break
                elif re.match(r"^PRETTY_NAME=\"Amazon Linux AMI [0-9]{4}\.[0-9]{2}", line):
                    distro = "alami"
                    break
                else:
                    distro = "unknown for /etc/os-release"
    return distro


def check_root():
    """Return whether the current user ID is 0 (root)."""
    return os.getegid() == 0


def verify_metadata():
    """Return whether the system can access the EC2 meta data and user data."""
    try:
        return requests.get("http://169.254.169.254/latest/meta-data/instance-id").status_code == 200
    except requests.exceptions.ConnectionError:
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
        profile_request = requests.get("http://169.254.169.254/latest/meta-data/profile")
    except requests.exceptions.ConnectionError:
        raise PrediagConnectionError("Failed to connect to AWS EC2 metadata service.")

    if profile_request.status_code == 200:
        profile = profile_request.text
    else:
        profile = "ERROR"
    return profile


class PrediagError(Exception):
    """Base class for exceptions in this module."""
    pass


class PrediagConnectionError(PrediagError):
    """A Requests ConnectionError occurred."""
    def __init__(self, error_message, *args):
        message = "Connection error: {}".format(error_message)
        super(PrediagConnectionError, self).__init__(message, *args)
