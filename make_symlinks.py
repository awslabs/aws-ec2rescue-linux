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
import filecmp
import os
import sys

# if called with relative paths, build absolute path off current-working directory
_callp = sys.argv[0]
if not os.path.isabs(_callp):
    _callp = os.path.abspath(_callp)
CALLPATH = os.path.split(_callp)[0]

# Find the duplicated files and replace the copies in the bin directory with symlinks to the copies two directories up
for module_dir_prefix in os.listdir(os.path.join(CALLPATH, "dist", "ec2rl", "bin")):
    os.chdir(os.path.join(CALLPATH, "dist", "ec2rl", "bin", module_dir_prefix))
    for same_file in filecmp.dircmp(os.path.join(CALLPATH, "dist", "ec2rl", "bin", module_dir_prefix),
                                    os.path.join(CALLPATH, "dist", "ec2rl")).same_files:
            print("Replacing '{}/{}' with a symlink".format(module_dir_prefix, same_file))
            os.remove(os.path.join(CALLPATH, "dist", "ec2rl", "bin", module_dir_prefix, same_file))
            os.symlink("../../{}".format(same_file), same_file)
