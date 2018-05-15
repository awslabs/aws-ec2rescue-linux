# Copyright 2016-2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
ModuleDir module

Functions:
    None

Classes:
    ModuleDir: list-like object that represents the modules loaded from a given directory path

Exceptions:
    ModuleDirError: base exception class for this module
    ModuleDirTypeError: raised when an item's type was not the expected type
    ModuleDirDuplicateModuleNameError: raised when adding a module when a module in the ModuleDir is using the same name
    ModuleDirModuleNotPresent: raised when attempting to remove a module that isn't present in the ModuleDir
"""
import os

from ec2rlcore.logutil import LogUtil
import ec2rlcore.module


class ModuleDir(list):
    """
    Given a directory path, create a list of Module objects created from the modules in the directory.

    Attributes:
        directory (str): the directory path of the module file as a string
        name (str): the file name of the module
        class_map (dict): dict whose keys:values are classes:lists of modules belonging to those classes
        domain_map (dict): dict whose keys:values are domains:lists of modules belonging to those domains
        name_map (dict): dict whose keys:values are module names:module objects
        language_map (dict): dict whose keys:values are languages:lists of modules implemented in those languages
        software_map (dict): dict whose keys:values are software programs:lists of modules using those executable
        package_map (dict): dict whose keys:values are software packages:lists of modules using those packages

    Methods:
        append: the list built-in append method plus mapping of the module
        extend: the list built-in extend which is not implemented for ModuleDir
        insert: the list built-in insert plus mapping of the module
        remove: the list built-in remove plus unmapping of the module
        pop: the list built-in pop which is not implemented for ModuleDir
        copy: overrides the built-in list copy in order to return a new ModuleDir using the soure ModuleDir's directory
        _map_module: adds the Module to the domain, class, and language mapping dicts
        _unmap_module: removes the Module from the domain, class, and language mapping dicts
        validate_constraints_have_args: validate whether a module should be run
    """

    def __init__(self, directory=None):
        """
        Perform initial configuration of the object. Files must end in ".yaml" and cannot start with ".".

        Parameters:
            directory (str): the directory path of the module file as a string
        """
        super(ModuleDir, self).__init__(self)
        self.logger = LogUtil.get_root_logger()
        self.logger.debug("moduledir.ModuleDir.__init__()")
        assert directory is not None
        self.directory = os.path.abspath(directory)
        self.name = os.path.basename(directory)
        # These dicts will provide mappings to the list enabling O(1) lookups at the cost of the up front work
        # Prepopulate keys with known values, where possible.
        self.class_map = {"collect": [], "gather": [], "diagnose": []}
        self.domain_map = {"net": [], "os": [], "performance": [], "application": []}
        self.name_map = {}
        self.language_map = {}
        self.software_map = {}
        self.package_map = {}

        # Populate self with Modules in directory
        for filename in sorted(os.listdir(directory)):
            # This use of str.startswith is basically "endswith"
            if not filename.startswith(".") and filename.startswith(".",
                                                                    len(filename) - len(".yaml"),
                                                                    len(filename)):
                try:
                    filename_with_path = os.path.join(directory, filename)
                    self.logger.debug("Adding file: {}".format(filename_with_path))
                    this_module = ec2rlcore.module.get_module(filename_with_path)
                    self.append(this_module)
                except ec2rlcore.module.ModuleConstraintParseError as mcpe:
                    self.logger.debug("{}: continuing with next module".format(mcpe))
                except ec2rlcore.module.ModuleConstraintKeyError as mcke:
                    self.logger.debug("{}: continuing with next module".format(mcke))
            else:
                self.logger.debug("Skipping hidden or non-yaml file {}.".format(filename))

    @property
    def classes(self):
        """Return the list of unique classes amongst the modules."""
        return sorted(list(self.class_map.keys()))

    @property
    def domains(self):
        """Return the list of unique domains amongst the modules."""
        return sorted(list(self.domain_map.keys()))

    def append(self, item):
        if not isinstance(item, ec2rlcore.module.Module):
            raise ModuleDirTypeError(item, "Module")

        if item.name in self.name_map:
            raise ModuleDirDuplicateModuleNameError(item.name)

        super(ModuleDir, self).append(item)
        self._map_module(item)

    def extend(self, *args, **kwargs):
        raise NotImplementedError()

    def insert(self, index, item):
        if not isinstance(index, int):
            raise ModuleDirTypeError(index, "int")

        if not isinstance(item, ec2rlcore.module.Module):
            raise ModuleDirTypeError(item, "ec2rlcore.module.Module")

        if item.name in self.name_map:
            raise ModuleDirDuplicateModuleNameError(item.name)

        super(ModuleDir, self).insert(index, item)
        self._map_module(item)

    def remove(self, item):
        if not isinstance(item, ec2rlcore.module.Module):
            raise ModuleDirTypeError(item, "ec2rlcore.module.Module")

        try:
            mapped_item = self.name_map[item.name]
            self._unmap_module(mapped_item)
            super(ModuleDir, self).remove(mapped_item)
        except KeyError:
            raise ModuleDirModuleNotPresent(item.name)

    def clear(self):
        for item in self:
            self.remove(item)

    def pop(self, *args, **kwargs):
        raise NotImplementedError()

    def copy(self):
        return ModuleDir(self.directory)

    def _map_module(self, module_obj):
        """Setup the module mappings for its class, domain, language, and name."""
        for class_name in module_obj.constraint["class"]:
            try:
                self.class_map[class_name].append(module_obj)
            # If the class doesn't yet have a list in the dict then add one
            except KeyError:
                self.class_map[class_name] = [module_obj]

        for domain_name in module_obj.constraint["domain"]:
            try:
                self.domain_map[domain_name].append(module_obj)
            # If the domain doesn't yet have a list in the dict then add one
            except KeyError:
                self.domain_map[domain_name] = [module_obj]

        for software_program in module_obj.constraint["software"]:
            try:
                self.software_map[software_program].append(module_obj)
            # If the software program doesn't yet have a list in the dict then add one
            except KeyError:
                self.software_map[software_program] = [module_obj]

        for package in module_obj.package:
            try:
                self.package_map[package].append(module_obj)
            # If the software package doesn't yet have a list in the dict then add one
            except KeyError:
                self.package_map[package] = [module_obj]

        if module_obj.language not in self.language_map:
            self.language_map[module_obj.language] = []
        # This should not need exception handling because modules with unsupported language values
        # are filtered during loading
        self.language_map[module_obj.language].append(module_obj)

        self.name_map[module_obj.name] = module_obj

    def _unmap_module(self, module_obj):
        """Remove references to this module from the class, domain, language, software, package, and name mappings."""
        for class_name in module_obj.constraint["class"]:
            self.class_map[class_name].remove(module_obj)
            if not self.class_map[class_name]:
                del self.class_map[class_name]

        for domain_name in module_obj.constraint["domain"]:
            self.domain_map[domain_name].remove(module_obj)
            if not self.domain_map[domain_name]:
                del self.domain_map[domain_name]

        for software_program in module_obj.constraint["software"]:
            self.software_map[software_program].remove(module_obj)
            if not self.software_map[software_program]:
                del self.software_map[software_program]

        for package in module_obj.package:
            self.package_map[package].remove(module_obj)
            if not self.package_map[package]:
                del self.package_map[package]

        self.language_map[module_obj.language].remove(module_obj)
        if not self.language_map[module_obj.language]:
            del self.language_map[module_obj.language]

        del self.name_map[module_obj.name]


class ModuleDirError(Exception):
    """Base class for exceptions in this module."""
    pass


class ModuleDirTypeError(ModuleDirError):
    """An object's type was not the expected type."""
    def __init__(self, foreign_item, expected_type):
        message = "Unexpected item of type: '{}'. Expected '{}'.".format(type(foreign_item).__name__, expected_type)
        super(ModuleDirTypeError, self).__init__(message)


class ModuleDirDuplicateModuleNameError(ModuleDirError):
    """Attempted to add module whose name is already used by an existing module."""
    def __init__(self, module_name):
        message = "Duplicate module detected: '{}'".format(module_name)
        super(ModuleDirDuplicateModuleNameError, self).__init__(message)


class ModuleDirModuleNotPresent(ModuleDirError):
    """Attempted to remove a module that is not present in the ModuleDir"""
    def __init__(self, module_name):
        message = "Failed to remove '{}'. Not present in instance of ModuleDir.".format(module_name)
        super(ModuleDirModuleNotPresent, self).__init__(message)
