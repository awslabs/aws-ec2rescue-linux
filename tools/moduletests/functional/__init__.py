# Copyright 2016-2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License  Version 2 0 (the "License")  You
# may not use this file except in compliance with the License  A copy of
# the License is located at
#
#     http //aws amazon com/apache2 0/
#
#
# or in the "license" file accompanying this file  This file is
# distributed on an "AS IS" BASIS  WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND  either express or implied  See the License for the specific
# language governing permissions and limitations under the License

"""
Init for module functional tets

Functions
    None

Classes
    None

Exceptions
    None
"""

from __future__ import print_function
import sys

if sys.hexversion < 0x3000000:
    # python2's raw_input() was renamed input() in python3 and python2's input() == eval(input())
    input = raw_input

print("=" * 120)
print("Running these functional tests will modify the local filesystem and system configuration ")
print("Test failures may result in system instability and/or inaccessibility ")
print("Only run these on a disposable test system!")
print("=" * 120)
are_you_sure = input("Are you sure you want to continue? [y/N] ")
if are_you_sure != "y":
    print("Functional tests aborted ")
    sys.exit(1)
