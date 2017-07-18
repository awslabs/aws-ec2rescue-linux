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
                    filename_with_path = os.sep.join([directory, filename])
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
        """Remove references to this module from the class, domain, language, and name mappings."""
        for class_name in module_obj.constraint["class"]:
            self.class_map[class_name].remove(module_obj)
            if not self.class_map[class_name]:
                del self.class_map[class_name]

        for domain_name in module_obj.constraint["domain"]:
            self.domain_map[domain_name].remove(module_obj)
            if not self.domain_map[domain_name]:
                del self.domain_map[domain_name]

        self.language_map[module_obj.language].remove(module_obj)
        if not self.language_map[module_obj.language]:
            del self.language_map[module_obj.language]

        del self.name_map[module_obj.name]

    # Formerly flubber()
    def validate_constraints_have_args(self, options=None, constraint=None, with_keys=None, without_keys=None):
        """
        Validate whether a module should be run given the constraints.

        First, each module is checked to see if it is still applicable. Modules that have already been marked as not
        applicable are skipped.

        Second, the module is checked to see if it was excluded via the command line args.

        Third, the constraint keys are filtered if with_keys or without_keys are provided. with_keys takes precedence
        over without_keys if both are specified (without_keys is not evaluated).

        Fourth, we attempt to match each constraint and constraint value to a corresponding constraint:value pair in
        the options. The module-specific options are checked then the global options are checked.

        constraint_retval is True when the constraint:value pair is found and False when it is not.
        module_retval is initialized to True and ANDed with the resulting constraint_retval after each constraint is
        checked. This keeps track of the overall success of the constraint checking.

        Parameters:
            options (Options): the Options instance containing the parsed constraints
            constraint (Constraint): the Constraints instance containing
            the combined constraint:value pairs of all modules
            with_keys (list): key list to be used for filtering (filter to only these keys)
            without_keys (list): key list to be used for filtering (filter to exclude these keys)

        Returns:
            True (bool)
        """
        self.logger.debug("moduledir.ModuleDir.validate_constraints_have_args()")

        # Validate whether each module can/should be run
        for mod in self:
            self.logger.debug("Validating module: {}".format(mod.name))
            # module_retval (boolean), represents whether a module's constraints have values
            module_retval = True

            # Keep earlier decisions about module acceptance (and their message)
            if not mod.applicable:
                continue

            # Check to see if module was excluded by name (--no=<module_name>)
            if mod.name in options.global_args and options.global_args[mod.name] == "False":
                self.logger.debug("module '{}' explicitly excluded with '--no={}'; skipping module".format(
                    mod.name, mod.name))
                mod.applicable = False
                mod.whyskipping = "explicitly excluded with '--no={}'.".format(mod.name)
                continue

            # Filter the constraints compared to include only the keys specified
            if with_keys:
                constraint_filtered_using = mod.constraint.with_keys
                key_list = with_keys
            # Filter the constraints compared to exclude the keys specified
            elif without_keys:
                constraint_filtered_using = mod.constraint.without_keys
                key_list = without_keys
            # All constraints will be compared
            else:
                constraint_filtered_using = mod.constraint.without_keys
                key_list = []
            self.logger.debug("key_list = {}".format(key_list))

            # Check current module's constraints against options
            for constraint_name in constraint_filtered_using(key_list).keys():
                self.logger.debug("'{}' constraint:values = '{}:{}'".format(
                    mod.name, constraint_name, mod.constraint[constraint_name]))

                # Skip optional constraints
                if constraint_name == "optional":
                    continue

                if constraint_name == "parallelexclusive":
                    continue

                def check_per_module_args(this_constraint_value):
                    """Check if this module has per-module args

                    Parameters:
                        this_constraint_value (str): the constraint whose value we ware looking for

                    Returns:
                        (bool): indicates whether a constraint value was found
                    """
                    if mod.name in options.per_module_args:
                        self.logger.debug("....Checking per_module_args")
                        # Check if this module's per-module args contains this constraint name as well as a value
                        if this_constraint_value in options.per_module_args[mod.name] and \
                                options.per_module_args[mod.name][this_constraint_value]:
                            self.logger.debug("........FOUND Constraint value is present")
                            return True
                        else:
                            self.logger.debug("......UNFOUND Constraint value is False (bool) or absent from "
                                              "options.per_module_args")
                            mod.whyskipping = "missing value for required argument '{}'.".format(this_constraint_value)
                            return False
                    return False

                def check_global_constraints(this_constraint_value):
                    """Check the global constraint:value pairs (options.global_args) for constraint:value pair

                    Parameters:
                        this_constraint_value (str): the constraint whose value we ware looking for

                    Returns:
                        (bool): indicates whether a constraint value was found
                    """
                    if this_constraint_value in options.global_args:
                        self.logger.debug("....Checking global_args")
                        self.logger.debug("......FOUND constraint name present in global_args")
                        # Check if this key has a value
                        if options.global_args[this_constraint_value]:
                            self.logger.debug("........FOUND Constraint value is present")
                            return True
                        else:
                            self.logger.debug("......UNFOUND Constraint value is False (bool) or absent from "
                                              "options.global_args")
                            mod.whyskipping = "missing value for required argument '{}'.".format(this_constraint_value)
                            return False
                    return False

                # Check each value of the named-set against the run-constraints and run-options
                for constraint_value in mod.constraint[constraint_name]:
                    self.logger.debug("Checking: {}:{}".format(constraint_name, constraint_value))
                    # constraint_retval (boolean) represents whether constraint has a value
                    if {constraint_name: constraint_value} in constraint:
                        self.logger.debug("..FOUND constraint:value pair present in the summation of constraints")
                        constraint_retval = True
                        module_retval = module_retval and constraint_retval
                        self.logger.debug("module_retval={}".format(module_retval))
                        # Found so go to the next constraint
                        continue

                    self.logger.debug("..UNFOUND constraint:value pair absent from summation of constraints")

                    # Run the additional checks
                    # Python short-circuits "and" and "or" operators so this is as efficient as a if/elif block while
                    # keeping the checks self-contained in their own functions
                    constraint_retval = check_per_module_args(constraint_value) or \
                        check_global_constraints(constraint_value)
                    # Add any new checks here, chaining off the constraint_retval assignment's "or" chain

                    # Handle cases where the constraint was found in neither options" global_args
                    # nor per_module_args
                    if not constraint_retval:
                        self.logger.debug("..UNFOUND {} absent from options".format(constraint_value))
                        mod.whyskipping = "missing required argument '{}'.".format(constraint_value)

                    self.logger.debug("..constraint_retval={}".format(constraint_retval))
                    # AND the module and constraint return values
                    # (any constraint failure causes the module to fail where fail = False)
                    module_retval = module_retval and constraint_retval
                    self.logger.debug("module_retval={}".format(module_retval))

                if not module_retval:
                    mod.applicable = False
        return True


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
