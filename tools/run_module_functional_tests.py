# Copyright 2016-2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
Run functional tests for modules.
"""
from __future__ import print_function
import os
import sys
import unittest


def main():
    # Add the root program directory and the module tests directory to sys.path
    call_paths = list()
    split_call_path_list = os.path.abspath(sys.argv[0]).split(os.sep)
    split_call_path_list[0] = "/"
    this_files_name = os.path.split(__file__)[-1]
    for file_name in [this_files_name, "tools"]:
        if split_call_path_list[-1] == file_name and file_name == "tools":
            call_paths.append(os.path.join(*split_call_path_list))
            split_call_path_list = split_call_path_list[0:-1]
        elif split_call_path_list[-1] == file_name:
            split_call_path_list = split_call_path_list[0:-1]
        else:
            print("Error parsing call path {} on token {}. Aborting.".format(os.path.join(*split_call_path_list),
                                                                             file_name))
            sys.exit(1)
    call_paths.append(os.path.join(*split_call_path_list))
    call_paths.append(os.path.join(call_paths[-1], "lib"))
    for call_path in call_paths:
        sys.path.insert(0, call_path)
    # Setup EC2RL_CALLPATH environment variable for modules to use
    os.environ["EC2RL_CALLPATH"] = os.path.join(*split_call_path_list)

    import ec2rlcore.prediag
    if not ec2rlcore.prediag.check_root():
        print("Functional tests must be run as root/with sudo! Aborting.")
        sys.exit(1)
    try:
        import moduletests.functional
        print("Running tests...")
        tests = unittest.TestLoader().discover(os.path.join(os.getcwd(), "moduletests", "functional"))
        # Due to the nature of the functional tests, failfast=True is set in order to limit the potential damage to
        # the system configuration in the event of bugs, test failures, etc.
        results = unittest.runner.TextTestRunner(failfast=True).run(tests)
        if not results.wasSuccessful():
            sys.exit(1)
    except Exception:
        print("Caught unhandled exception!")
        raise


if __name__ == "__main__":
    main()
