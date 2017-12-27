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
Converts module .yaml files to .py for unit testing purposes

Functions:
    convert: Performs the actual conversion. Creates a constructor for the yaml tag, creates a directory, and then
    converts the files.

Classes:
    modloader: Used to ignore the ec2rlcore.module.Module yaml tag as we do not need it

"""
from __future__ import print_function
import os
import sys

# Add the vendored lib directory to sys.path and change the working directory to the moduletest directory.
call_paths = list()
split_call_path_list = os.path.abspath(sys.argv[0]).split(os.sep)
split_call_path_list[0] = "/"
this_files_name = os.path.split(__file__)[-1]
for file_name in [this_files_name, "moduletests", "tools"]:
    if split_call_path_list[-1] == file_name and file_name == this_files_name:
        split_call_path_list = split_call_path_list[0:-1]
        os.chdir(os.path.join(*split_call_path_list))
    elif split_call_path_list[-1] == file_name:
        split_call_path_list = split_call_path_list[0:-1]
    else:
        print("Error parsing call path '{}' on token '{}'. Aborting.".format(os.path.join(*split_call_path_list),
                                                                             file_name))
        sys.exit(1)
root_ec2rl_dir = os.path.join(*split_call_path_list)
sys.path.insert(0, root_ec2rl_dir)
import yaml


class ModLoader(yaml.SafeLoader):
    """
    Class from yaml.SafeLoader used for overriding the need to parse the yaml tag.

    Methods:
        ignoretag: Return a construct mapping for yaml.SafeLoader's use
    """
    def ignoretag(self, node):
        """
        Ignores the passed tag for yaml construction purposes

        Returns:
            construct_mapping: A construct mapping for the node
        """
        return self.construct_mapping(node)


def main():
    """
    Convert Python modules from ec2rl/mod.d/ from their yaml form to .py files for unit testing

    Returns:
        True (bool)
    """
    ModLoader.add_constructor("!ec2rlcore.module.Module", ModLoader.ignoretag)

    mod_src_dir = os.path.join(os.getcwd(), "src")
    try:
        os.stat(mod_src_dir)
    except Exception:
        os.mkdir(mod_src_dir)

    try:
        for mod_file_name in os.listdir(os.path.join(root_ec2rl_dir, "mod.d")):
            with open(os.path.join(root_ec2rl_dir, "mod.d", mod_file_name), "r") as yamlfile:
                module = yaml.load(yamlfile, Loader=ModLoader)
                if module["language"] == "python":
                    mod_src_path = os.path.join(mod_src_dir, "{}.py".format(module["name"]))
                    with open(mod_src_path, "w") as pyfile:
                        pyfile.write(module["content"])
                    print("Wrote: {}".format(mod_src_path))
        print("Conversion complete.")
    except Exception as ex:
        print(ex)
        print("Conversion failed. Please review the exception to resolve")


if __name__ == "__main__":
    main()
