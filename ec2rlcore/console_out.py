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
Console Output module.
Contains helpers for writing output to the console, and creating the diagnostics summary output

Functions:
    notify_module_running: Prints message to user indicating the given module is running

Classes:
    None

Exceptions:
    None
"""
from __future__ import print_function

import ec2rlcore.logutil
import ec2rlcore.module
import threading
import sys


logger = ec2rlcore.logutil.LogUtil.get_root_logger()
_print_lock = threading.Lock()
_first_module = True


def notify_module_running(mod):
    """
    Prints message to notify user that the given module is running

    Parameters:
        mod (ec2rlcore.Module): module to print notification about

    Returns:
        True
    """
    global _first_module

    _print_lock.acquire()
    try:
        if _first_module:
            print("Running Modules:")
            print(mod.name, end="")
            _first_module = False
        else:
            print(", {}".format(mod.name), end="")
        logger.info("Running {}".format("module " + mod.placement + "/" + mod.name))
        sys.stdout.flush()
    finally:
        _print_lock.release()

    return True
