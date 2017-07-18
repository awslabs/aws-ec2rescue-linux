# Copyright 2016-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/


# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""
Init

Functions:
    None

Classes:
    None

Exceptions:
    None
"""
import os
import platform
import sys

import ec2rlcore.logutil

__all__ = ["awshelpers", "backup", "console_out",
           "constraint", "logutil", "main",
           "menu", "menu_config", "menu_item",
           "menu_textpad_mod", "module", "moduledir",
           "options", "paralleldiagnostics", "prediag",
           "programversion", "s3upload"]

if sys.hexversion < 0x2070000:
    print("ec2rl requires Python 2.7+, but running version is {0}.".format(
        platform.python_version()))
    sys.exit(201)

dual_log = ec2rlcore.logutil.LogUtil.dual_log_info

# Add vendored library directories to sys.path
_callp = sys.argv[0]
if not os.path.isabs(_callp):
    _callp = os.path.abspath(_callp)
# Modules whose implementation is the same for Python2/3
sys.path.insert(0, "{}/lib".format(os.path.split(_callp)[0]))

# Modules whose implementation differs between Python2/3
if sys.hexversion >= 0x3000000:
    sys.path.insert(0, "{}/lib/python3".format(os.path.split(_callp)[0]))
else:
    sys.path.insert(0, "{}/lib/python2".format(os.path.split(_callp)[0]))
