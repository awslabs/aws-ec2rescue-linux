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
from __future__ import print_function
import distutils.sysconfig
import os
import shutil
import subprocess
import sys

import ec2rlcore.moduledir

# Example: /usr/lib
LIBPATH = distutils.sysconfig.get_config_var("LIBDIR")
# Example: /usr/include/python3.5m
INCLUDEPATH = distutils.sysconfig.get_python_inc()
# Example: python3.5m
PYLIBNAME = distutils.sysconfig.get_config_var('LIBRARY')[3:-2]

# if called with relative paths, build absolute path off current-working directory
_callp = sys.argv[0]
if not os.path.isabs(_callp):
    _callp = os.path.abspath(_callp)
CALLPATH = os.path.split(_callp)[0]
BINPATH = os.sep.join((os.path.split(_callp)[0], "bin"))

all_modules = dict()
all_modules["pre.d"] = ec2rlcore.moduledir.ModuleDir("{}/pre.d".format(CALLPATH))
all_modules["mod.d"] = ec2rlcore.moduledir.ModuleDir("{}/mod.d".format(CALLPATH))
all_modules["post.d"] = ec2rlcore.moduledir.ModuleDir("{}/post.d".format(CALLPATH))

# Build the directory structure, if needed
if not os.path.isdir(os.sep.join((CALLPATH, "bin", "pre.d"))):
    os.makedirs(os.sep.join((CALLPATH, "bin", "pre.d")))
if not os.path.isdir(os.sep.join((CALLPATH, "bin", "mod.d"))):
    os.makedirs(os.sep.join((CALLPATH, "bin", "mod.d")))
if not os.path.isdir(os.sep.join((CALLPATH, "bin", "post.d"))):
    os.makedirs(os.sep.join((CALLPATH, "bin", "post.d")))

for module_dir_prefix in all_modules.keys():
    for module_obj in all_modules[module_dir_prefix]:
        if module_obj.language == "python":
            try:
                # Replace replace the language value with "binary"
                module_data = None
                with open(os.sep.join((CALLPATH, module_dir_prefix, module_obj.name + ".yaml")), "r") as module_file:
                    module_data = module_file.read()
                    module_data = module_data.replace("language: !!str python", "language: !!str binary")
                with open(os.sep.join((CALLPATH, module_dir_prefix, module_obj.name + ".yaml")), "w") as module_file:
                    module_file.write(module_data)
                with open(os.sep.join((BINPATH, module_dir_prefix, module_obj.name + ".py")), "w") as module_file:
                    module_file.write(module_obj.content)
                subprocess.check_call(["pyinstaller",
                                       os.sep.join((BINPATH, module_dir_prefix, module_obj.name + ".py"))])
                # Copy the resulting files to bin/mod.d
                # shutil.copy will overwrite which is desirable as the intention is to consolidate the compiled
                # modules into a single directory.
                for file in os.listdir(os.sep.join((CALLPATH, "dist", module_obj.name))):
                    shutil.copy(os.sep.join((CALLPATH, "dist", module_obj.name, file)),
                                os.sep.join((BINPATH, module_dir_prefix)))
            except subprocess.CalledProcessError as cpe:
                print(cpe.output)
                print("Error converting module {}/{}".format(module_obj.placement, module_obj.name))
            finally:
                # Cleanup, but check if these exist first. An exception could have occurred prior to their creation.
                if os.path.isfile(os.sep.join((BINPATH, module_dir_prefix, module_obj.name + ".py"))):
                    os.remove(os.sep.join((BINPATH, module_dir_prefix, module_obj.name + ".py")))
                if os.path.isfile(os.sep.join((CALLPATH, module_obj.name + ".spec"))):
                    os.remove(os.sep.join((CALLPATH, module_obj.name + ".spec")))
                if os.path.isdir(os.sep.join((CALLPATH, "dist", module_obj.name))):
                    shutil.rmtree(os.sep.join((CALLPATH, "dist", module_obj.name)))
                if os.path.isdir(os.sep.join((CALLPATH, "build", module_obj.name))):
                    shutil.rmtree(os.sep.join((CALLPATH, "build", module_obj.name)))

            print("Converted: {}/{}".format(module_obj.placement, module_obj.name))

    if os.path.isdir(os.sep.join((BINPATH, module_dir_prefix, "__pycache__"))):
        shutil.rmtree(os.sep.join((BINPATH, module_dir_prefix, "__pycache__")))
