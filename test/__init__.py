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
Init for testing. Disable logging to speed up test execution.

Functions:
    None

Classes:
    None

Exceptions:
    None
"""
import logging
import os
import sys

# Disable unnecessary logging to speed up test times
logging.disable(logging.CRITICAL)

# Add lib folder to path so we can import vendored modules
_callp = sys.argv[0]
if not os.path.isabs(_callp):
    _callp = os.path.abspath(_callp)
callpath = os.path.split(_callp)[0]
sys.path.append("{}/lib".format(callpath))
