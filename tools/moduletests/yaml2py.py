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
import yaml

class modloader(yaml.SafeLoader):
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

def convert():
    """
    Converts python modules from ec2rl/mod.d/ from their yaml form to .py files for unit testing

    Returns:
        True (bool)
    """
    modloader.add_constructor(
        u'!ec2rlcore.module.Module',
        modloader.ignoretag)

    directory = "src/"
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)

    try:
        for i in os.listdir("../../mod.d"):
            with open ("../../mod.d/" + i, "r") as yamlfile:
                module = yaml.load(yamlfile, Loader=modloader)
                language = module["language"]
                name = module["name"]
                content = module["content"]
                if language == "python":
                    with open (directory + name + ".py", "w") as pyfile:
                        pyfile.write(content)
                    print(directory + name + ".py")
        print("Conversion complete.")
    except Exception as ex:
        print(ex)
        print("Conversion failed. Please review the exception to resolve")

convert()

