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
This is the programversion module.

Functions:
    None

Classes:
    ProgramVersion: object representation of a four-piece version number.

Exceptions:
    ProgramVersionError: base exception class for this module
    VersionParsingError: raised when the given version string doesn't conform to the expected standard
    InvalidComparisonError: raised when a ProgramVersion object is compared to a non-like object
"""
import re


class ProgramVersion(object):
    """
    Object class that provides version representation with multiple parts.
    Implements string representation for printing as well as comparison operators for comparing like objects.

    Attributes:
        major (int): the major version number
        minor (int): the minor version number
        maintenance (int): the maintenance version number
        pre_release (int): the pre_release version number
        release (str): the release type
        release_short (str): the single char, shorthand release type
        release_numerical (int): integer representation of the release for comparison purposes
    """

    def __init__(self, version_string):
        """
        Parameters:
            version_string (string): version string in the form of:
                [major version].[minor version].[maintenance version][release type shorthand][pre-release version]
                Example: 1.0.0a1
        """
        # regex below is provided in PEP 440
        # post releases have been excluded (bump the maintenance number instead)
        # dev releases have been excluded (these should already be alpha/beta/rc releases)
        if not re.match(r"\A([1-9]\d*!)?(0|[1-9]\d*)(\.(0|[1-9]\d*))*((a|b|rc)(0|[1-9]\d*))?\Z", version_string):
            raise ProgramVersionParsingError(version_string)
        self.major, self.minor, remaining = version_string.split(".")
        self.release_short = ""
        if len(re.split(r"(a|b|rc)", remaining)) == 1:
            self.maintenance = remaining
        else:
            self.maintenance, self.release_short, self.pre_release = re.split(r"(a|b|rc)", remaining)
        if self.release_short == "a":
            self.release = "alpha"
            self.release_numerical = 1
        elif self.release_short == "b":
            self.release = "beta"
            self.release_numerical = 2
        elif self.release_short == "rc":
            self.release = "candidate"
            self.release_numerical = 3
        else:
            self.release_short = "r"
            self.pre_release = "0"
            self.release = "release"
            self.release_numerical = 4

    def __repr__(self):
        """
        Implementation of __repr__ enables customization of how an object instance is 'printed' when used as
        an argument of print().
        For example (from ec2lcore.main.Main): 'print("ec2rl {}".format(self.PROGRAM_VERSION))' prints:
        'ec2rl 1.0.0b6'
        """
        if self.release_short == "r":
            return "{}.{}.{}".format(self.major, self.minor, self.maintenance)
        else:
            return "{}.{}.{}{}{}".format(self.major, self.minor, self.maintenance, self.release_short, self.pre_release)

    def __len__(self):
        """Implementation enables the builtin len() function to return the length of the string representation."""
        return len(self.__repr__())

    def __eq__(self, other):
        """Implenentation enables the rich comparison operator '=='."""
        if isinstance(other, self.__class__):
            return int(self.major) == int(other.major) and \
                   int(self.minor) == int(other.minor) and \
                   int(self.maintenance) == int(other.maintenance) and \
                   int(self.release_numerical) == int(other.release_numerical) and \
                   int(self.pre_release) == int(other.pre_release)
        raise ProgramVersionInvalidComparisonError(type(other))

    def __ne__(self, other):
        """Implementation enables the rich comparison operator '!='."""
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        raise ProgramVersionInvalidComparisonError(type(other))

    def __lt__(self, other):
        """
        Implementation enables the rich comparison operator '<'.
        Python 2.5+ will infer the other operators, le, gt, and ge.
        """
        if isinstance(other, self.__class__):
            return int(other.major) > int(self.major) \
                   or (int(other.major) == int(self.major) and
                       int(other.minor) > int(self.minor)) \
                   or (int(other.major) == int(self.major) and
                       int(other.minor) == int(self.minor) and
                       int(other.maintenance) > int(self.maintenance)) \
                   or (int(other.major) == int(self.major) and
                       int(other.minor) == int(self.minor) and
                       int(other.maintenance) == int(self.maintenance) and
                       other.release_numerical > self.release_numerical) \
                   or (int(other.major) == int(self.major) and
                       int(other.minor) == int(self.minor) and
                       int(other.maintenance) == int(self.maintenance) and
                       other.release_numerical == self.release_numerical and
                       int(other.pre_release) > int(self.pre_release))
        raise ProgramVersionInvalidComparisonError(type(other))


class ProgramVersionError(Exception):
    """Base class for exceptions in this module."""
    pass


class ProgramVersionParsingError(ProgramVersionError):
    """An invalid version string was encountered."""
    def __init__(self, version_string, *args):
        message = "Invalid version string: '{}'. Example correct version string: 1.0.0rc1." \
                  " For formatting details see PEP 440.".format(version_string)
        super(ProgramVersionParsingError, self).__init__(message, *args)


class ProgramVersionInvalidComparisonError(ProgramVersionError):
    """A ProgramVersion was compared with another object of a different type."""
    def __init__(self, other_type, *args):
        message = "Invalid comparison of 'ProgramVersion' object with object of type '{}'.".format(other_type)
        super(ProgramVersionInvalidComparisonError, self).__init__(message, *args)
