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
Run unit tests for modules.
"""
from __future__ import print_function
import os
import sys
import unittest

import coverage


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
    for call_path in call_paths:
        sys.path.insert(0, call_path)

    try:
        print("Running tests...")
        code_coverage = coverage.Coverage(branch=True, source=["moduletests/src/"])
        code_coverage.start()
        tests = unittest.TestLoader().discover(os.path.join(os.getcwd(), "moduletests", "unit"))
        results = unittest.runner.TextTestRunner().run(tests)
        if not results.wasSuccessful():
            sys.exit(1)
        code_coverage.stop()
        code_coverage.save()
        code_coverage.report()
    except Exception:
        print("Caught unhandled exception!")
        raise


if __name__ == "__main__":
    main()
