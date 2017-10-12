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

"""Unit tests for "moduledir" module."""
try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

import copy
import os
import sys
import unittest

import ec2rlcore.constraint
import ec2rlcore.module
import ec2rlcore.moduledir
import ec2rlcore.options

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib


class TestModuleDir(unittest.TestCase):
    """Testing class for "moduledir" unit tests."""
    module_path = ""
    module = ""

    argv_backup = sys.argv
    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    if os.path.isdir(_callp):
        callpath = _callp
    else:
        callpath = os.path.split(_callp)[0]

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()
        sys.argv = self.argv_backup

    def test_moduledir_postdiagnostic_instantiation(self):
        """
        Check that running the ModuleDir class returns an instance of ModuleDir and contains the expected number of
        modules. Tests post.d code path.
        """
        module_path = os.path.join(self.callpath, "test/modules/post.d")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        self.assertIsInstance(modules, ec2rlcore.moduledir.ModuleDir)
        self.assertEqual(len(modules), 1)

    def test_moduledir_run_instantiation(self):
        """
        Check that running the ModuleDir class returns an instance of ModuleDir and contains the expected number of
        modules. Tests mod.d code path.
        """
        module_path = os.path.join(self.callpath, "test/modules/mod.d/")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        self.assertIsInstance(modules, ec2rlcore.moduledir.ModuleDir)
        self.assertEqual(len(modules), 112)

    def test_moduledir_instantiation_failure_keyerror(self):
        """Check the ModuleDir list doesn't add a module missing a constraint."""
        module_path = os.path.join(self.callpath, "test/modules/test_moduledir_instantiation_failure_keyerror/")
        with contextlib.redirect_stdout(self.output):
            module_list = ec2rlcore.moduledir.ModuleDir(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_class.yaml' missing required constraint 'class'.\n")
        self.assertFalse(module_list)

    def test_moduledir_instantiation_failure_parseerror(self):
        """Check the ModuleDir list doesn't add a module with a malformed constraint."""
        module_path = os.path.join(self.callpath, "test/modules/test_moduledir_instantiation_failure_parseerror/")
        module_list = ec2rlcore.moduledir.ModuleDir(module_path)
        self.assertFalse(module_list)

    def test_moduledir_instantiation_new_map_keys(self):
        """
        Check that running the ModuleDir class returns an instance of ModuleDir and contains the expected number of
        modules. Tests mod.d code path.
        """
        module_path = os.path.join(self.callpath, "test/modules/test_moduledir_instantiation_new_map_keys")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        self.assertIsInstance(modules, ec2rlcore.moduledir.ModuleDir)
        self.assertEqual(len(modules), 1)
        self.assertTrue("test_class" in modules.class_map.keys())
        self.assertTrue("test_domain" in modules.domain_map.keys())
        self.assertTrue("ex" in modules.name_map.keys())
        self.assertTrue("bash" in modules.language_map.keys())
        self.assertTrue("test_software" in modules.software_map.keys())
        self.assertTrue("test_package https://aws.amazon.com/" in modules.package_map.keys())

    def test_moduledir_append_module_missing_class_value(self):
        """Check the ModuleDir list doesn't add an empty class value."""
        good_module_path = os.path.join(self.callpath, "test/modules/mod.d/")
        bad_module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_classvalue.yaml")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)

        good_classes = copy.deepcopy(module_list.classes)

        module_list.append(ec2rlcore.module.get_module(bad_module_path))
        self.assertEqual(good_classes, module_list.classes)

    def test_moduledir_append_module_missing_domain_value(self):
        """Check the ModuleDir list doesn't add an empty domain value."""
        good_module_path = os.path.join(self.callpath, "test/modules/mod.d/")
        bad_module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_domainvalue.yaml")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)

        good_domains = copy.deepcopy(module_list.domains)

        module_list.append(ec2rlcore.module.get_module(bad_module_path))
        self.assertEqual(good_domains, module_list.domains)

    def test_moduledir_append_moduledirtypeerror(self):
        """
        Check that ModuleDir raises a ModuleDirTypeError when trying to append an item that isn't of 
        type ec2rlcore.module.Module.
        """
        good_module_path = os.path.join(self.callpath, "test/modules/mod.d/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        with self.assertRaises(ec2rlcore.moduledir.ModuleDirTypeError):
            module_list.append("a")

    def test_moduledir_append_duplicatemodulenameerror(self):
        """
        Check that ModuleDir raises a ModuleDirDuplicateModuleNameError when trying to append a module with a name
        that is already in the ModuleDir.
        """
        good_module_path = os.path.join(self.callpath, "test/modules/mod.d/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        duplicate_module = ec2rlcore.module.get_module(os.path.join(good_module_path, "ex.yaml"))
        with self.assertRaises(ec2rlcore.moduledir.ModuleDirDuplicateModuleNameError):
            module_list.append(duplicate_module)

    def test_moduledir_notimplemented_methods(self):
        """Test that unimplemented methods raise NotImplementedError."""
        good_module_path = os.path.join(self.callpath, "test/modules/mod.d/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        with self.assertRaises(NotImplementedError):
            module_list.extend(["some_value"])
        with self.assertRaises(NotImplementedError):
            module_list.pop()

    def test_moduledir_remove_moduledirtypeerror(self):
        """
        Check that ModuleDir raises a ModuleDirTypeError when trying to remove an item that isn't of 
        type ec2rlcore.module.Module.
        """
        good_module_path = os.path.join(self.callpath, "test/modules/mod.d/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        with self.assertRaises(ec2rlcore.moduledir.ModuleDirTypeError):
            module_list.remove("a")

    def test_moduledir_remove_moduledirmodulenotpresent(self):
        """
        Check that ModuleDir raises a ModuleDirTypeError when trying to remove an item that isn't of 
        type ec2rlcore.module.Module.
        """
        good_module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        module_path = os.path.join(self.callpath, "test/modules/mod.d/atop.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        with self.assertRaises(ec2rlcore.moduledir.ModuleDirModuleNotPresent):
            module_list.remove(module_obj)

    def test_moduledir_copy(self):
        """Test that copy() returns a new instance of the ModuleDir based on the ModuleDir.directory attribute."""
        good_module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        new_module_list = module_list.copy()
        self.assertEqual(new_module_list.directory, module_list.directory)
        self.assertEqual(len(new_module_list), len(module_list))
        self.assertEqual(new_module_list.class_map.keys(), module_list.class_map.keys())
        self.assertEqual(new_module_list.domain_map.keys(), module_list.domain_map.keys())
        self.assertEqual(new_module_list.name_map.keys(), module_list.name_map.keys())
        self.assertEqual(new_module_list.language_map.keys(), module_list.language_map.keys())
        self.assertEqual(new_module_list.software_map.keys(), module_list.software_map.keys())
        self.assertEqual(new_module_list.package_map.keys(), module_list.package_map.keys())

    def test_moduledir_insert(self):
        """Test that inserting a module adds the module to the expected list postion and updates the mappings."""
        good_module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        module_path = os.path.join(self.callpath, "test/modules/mod.d/atop.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        module_list.insert(0, module_obj)
        self.assertTrue(module_list[0].name == "atop")
        self.assertTrue("diagnose" in module_list.class_map.keys())
        self.assertTrue("net" in module_list.domain_map.keys())
        self.assertTrue("atop" in module_list.name_map.keys())
        self.assertTrue("bash" in module_list.language_map.keys())
        self.assertTrue("atop" in module_list.software_map.keys())
        self.assertTrue("atop https://www.atoptool.nl/" in module_list.package_map.keys())

    def test_moduledir_insert_index_typeerror(self):
        """Test that specifying a non-integer index with the insert() method will raise ModuleDirTypeError."""
        good_module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        module_path = os.path.join(self.callpath, "test/modules/mod.d/atop.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        with self.assertRaises(ec2rlcore.moduledir.ModuleDirTypeError):
            module_list.insert("0", module_obj)

    def test_moduledir_insert_item_typeerror(self):
        """Test that specifying a non-Module item with the insert() method will raise ModuleDirTypeError."""
        good_module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        with self.assertRaises(ec2rlcore.moduledir.ModuleDirTypeError):
            module_list.insert(0, "hello")

    def test_moduledir_insert_duplicatename(self):
        """test that inserting a Module of the same name will raise a ModuleDirDuplicateModuleNameError."""
        good_module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        module_list = ec2rlcore.moduledir.ModuleDir(good_module_path)
        module_path = os.path.join(self.callpath, "test/modules/mod.d/atop.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        module_list.insert(0, module_obj)
        with self.assertRaises(ec2rlcore.moduledir.ModuleDirDuplicateModuleNameError):
            module_list.insert(0, module_obj)

    def test_moduledir_module_req_validation_all_keys(self):
        """Test validate_constraints_have_args when with_keys is empty, meaning test all keys."""
        module_path = os.path.join(self.callpath, "test/modules/test_moduledir_module_req_validation")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        sys.argv = ["ec2rl", "run", "--times=1", "--period=5"]
        options = ec2rlcore.options.Options(subcommands=["run", "list", "help", "menuconfig", "saveconfig", "upload"])
        constraint = ec2rlcore.constraint.Constraint()

        for module_obj in modules:
            constraint.update(module_obj.constraint.with_keys(["domain", "class", "distro", "software", "perfimpact"]))

        ret = modules.validate_constraints_have_args(options=options,
                                                     constraint=constraint,
                                                     without_keys=[])
        # validate_constraints_have_args() returns True at the end of execution
        self.assertTrue(ret)

        # These will fail because the superfluous key comparisons as a result of not filtering the keys.
        for module_obj in modules:
            if module_obj.name == "arpcache":
                self.assertFalse(module_obj.applicable)
            if module_obj.name == "atop":
                self.assertFalse(module_obj.applicable)

    def test_moduledir_module_req_validation_without_keys(self):
        """Test validate_constraints_have_args when using without_keys to filter the key list."""
        module_path = os.path.join(self.callpath, "test/modules/test_moduledir_module_req_validation")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        sys.argv = ["ec2rl", "run"]
        options = ec2rlcore.options.Options(subcommands=["run", "list", "help", "menuconfig", "saveconfig", "upload"])
        constraint = ec2rlcore.constraint.Constraint()
        for module_obj in modules:
            constraint.update(module_obj.constraint.with_keys(["domain", "class", "distro", "software", "perfimpact"]))

        ret = modules.validate_constraints_have_args(options=options,
                                                     constraint=constraint,
                                                     without_keys=["software", "distro", "sudo", "requires_ec2"])
        # validate_constraints_have_args() returns True at the end of execution
        self.assertTrue(ret)

        for module_obj in modules:
            if module_obj.name == "arpcache":
                self.assertTrue(module_obj.applicable)
            if module_obj.name == "atop":
                # atop will fail because the "period" and "times" constraints are not satisfied.
                self.assertFalse(module_obj.applicable)

    def test_moduledir_module_req_validation_with_keys(self):
        """Test validate_constraints_have_args when using with_keys to filter the key list."""
        module_path = os.path.join(self.callpath, "test/modules/test_moduledir_module_req_validation")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        sys.argv = ["ec2rl", "run"]
        options = ec2rlcore.options.Options(subcommands=["run", "list", "help", "menuconfig", "saveconfig", "upload"])
        constraint = ec2rlcore.constraint.Constraint()
        for module_obj in modules:
            constraint.update(module_obj.constraint.with_keys(["domain", "class", "distro", "software", "perfimpact"]))

        ret = modules.validate_constraints_have_args(options=options,
                                                     constraint=constraint,
                                                     with_keys=["required"])
        # validate_constraints_have_args() returns True at the end of execution
        self.assertTrue(ret)

        for module_obj in modules:
            if module_obj.name == "arpcache":
                self.assertTrue(module_obj.applicable)
            if module_obj.name == "atop":
                # atop will fail because the "period" and "times" constraints are not satisfied.
                self.assertFalse(module_obj.applicable)

    def test_moduledir_module_req_validation_with_global_args(self):
        """Test validate_constraints_have_args when module constraints are in the global_args dict."""
        module_path = os.path.join(self.callpath, "test/modules/test_moduledir_module_req_validation")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        sys.argv = ["ec2rl", "run", "--times=1", "--period="]
        options = ec2rlcore.options.Options(subcommands=["run", "list", "help", "menuconfig", "saveconfig", "upload"])
        constraint = ec2rlcore.constraint.Constraint()
        for module_obj in modules:
            constraint.update(module_obj.constraint.with_keys(["domain", "class", "distro", "software", "perfimpact"]))

        ret = modules.validate_constraints_have_args(options=options,
                                                     constraint=constraint,
                                                     with_keys=["required"])
        # validate_constraints_have_args() returns True at the end of execution
        self.assertTrue(ret)

        for module_obj in modules:
            if module_obj.name == "arpcache":
                self.assertTrue(module_obj.applicable)
            elif module_obj.name == "atop":
                # The "times" constraint is satisfied, but "period" is not because there is no value to match the key
                self.assertFalse(module_obj.applicable)

    def test_moduledir_module_req_validation_with_module_exclusion(self):
        """Test validate_constraints_have_args when a module is specifically excluded via --no=<module_name>."""
        module_path = os.path.join(self.callpath, "test/modules/test_moduledir_module_req_validation")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        sys.argv = ["ec2rl", "run", "--times=1", "--period=5", "--no=atop"]
        options = ec2rlcore.options.Options(
            subcommands=["run", "list", "help", "menuconfig", "saveconfig", "upload"])
        constraint = ec2rlcore.constraint.Constraint()
        for module_obj in modules:
            constraint.update(
                module_obj.constraint.with_keys(["domain", "class", "distro", "software", "perfimpact"]))

        ret = modules.validate_constraints_have_args(options=options,
                                                     constraint=constraint,
                                                     with_keys=["required"])
        # validate_constraints_have_args() returns True at the end of execution
        self.assertTrue(ret)

        for module_obj in modules:
            if module_obj.name == "arpcache":
                self.assertTrue(module_obj.applicable)
            elif module_obj.name == "atop":
                # atop will fail because, despite having all the constraints met, it was excluded via --no=atop.
                self.assertFalse(module_obj.applicable)

    def test_moduledir_module_req_validation_with_per_module_args(self):
        """Test validate_constraints_have_args when module constraints are in the per_module_args dict."""
        module_path = os.path.join(self.callpath, "test/modules/test_moduledir_module_req_validation")
        modules = ec2rlcore.moduledir.ModuleDir(module_path)
        sys.argv = ["ec2rl", "run"]
        options = ec2rlcore.options.Options(subcommands=["run", "list", "help", "menuconfig", "saveconfig", "upload"])
        options.per_module_args["atop"] = {}
        options.per_module_args["atop"]["times"] = 1
        constraint = ec2rlcore.constraint.Constraint()
        for module_obj in modules:
            constraint.update(module_obj.constraint.with_keys(["domain", "class", "distro", "software", "perfimpact"]))

        ret = modules.validate_constraints_have_args(options=options,
                                                     constraint=constraint,
                                                     with_keys=["required"])
        # validate_constraints_have_args() returns True at the end of execution
        self.assertTrue(ret)

        for module_obj in modules:
            if module_obj.name == "arpcache":
                self.assertTrue(module_obj.applicable)
            elif module_obj.name == "atop":
                # atop will fail because the "period" constraint has not been satisfied.
                self.assertFalse(module_obj.applicable)

        # Test maintaining prior module invalidations
        options.per_module_args["atop"]["period"] = 5
        modules.validate_constraints_have_args(options=options,
                                               constraint=constraint,
                                               with_keys=["required"])

        for module_obj in modules:
            if module_obj.name == "arpcache":
                self.assertTrue(module_obj.applicable)
            elif module_obj.name == "atop":
                # atop will fail again, despite the unsatisfied constraint being corrected, because prior failures are
                # checked at the beginning of validate_constraints_have_args().
                self.assertFalse(module_obj.applicable)

if __name__ == "__main__":
    unittest.main()
