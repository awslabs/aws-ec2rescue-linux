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

"""Unit tests for "module" module."""
try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

import os
import sys
import unittest

import ec2rlcore.module
import ec2rlcore.options

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib


class TestModule(unittest.TestCase):
    """Testing class for "module" unit tests."""
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
        sys.argv = ["test/modules/not_a_real_file", "run", "--abc=def"]
        self.module_path = os.path.join(self.callpath, "test/modules/mod.d/ex.yaml")
        self.module = ec2rlcore.module.get_module(self.module_path)

        for x in ("EC2RL_WORKDIR",
                  "EC2RL_RUNDIR",
                  "EC2RL_LOGDIR",
                  "EC2RL_GATHEREDDIR",
                  "EC2RL_DISTRO",
                  "EC2RL_NET_DRIVER",
                  "EC2RL_VIRT_TYPE",
                  "EC2RL_SUDO",
                  "EC2RL_PERFIMPACT",
                  "EC2RL_CALLPATH"):
            os.environ[x] = "test"

    def tearDown(self):
        self.output.close()
        sys.argv = self.argv_backup

    def test_module_name(self):
        """Check that module name was set correctly."""
        self.assertEqual(self.module.name, "ex")

    def test_module_path(self):
        """Check that module path is set correctly."""
        self.assertEqual(self.module.path, self.module_path)

    def test_module_path_fail(self):
        """Check that module gracefully fails if path doesn"t exist."""
        module_path = "nowhere/mod.d/ex.yaml"
        with self.assertRaises(ec2rlcore.module.ModulePathError):
            ec2rlcore.module.get_module(module_path)

    def test_module_logger(self):
        """Check that logger was set."""
        import logging
        self.assertIsInstance(self.module.logger, logging.Logger)

    def test_module_placement_run(self):
        """Check that module set itself to "run" placement."""
        self.assertEqual(self.module.placement, "run")

    def test_module_placement_prediagnostic(self):
        """Check that module set itself to "prediagnostic" placement."""
        module_path = os.path.join(self.callpath, "test/modules/pre.d/ex.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        self.assertEqual(module_obj.placement, "prediagnostic")

    def test_module_placement_postdiagnostic(self):
        """Check that module set itself to "postdiagnostic" placement."""
        module_path = os.path.join(self.callpath, "test/modules/post.d/ex.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        self.assertEqual(module_obj.placement, "postdiagnostic")

    def test_module_constraint(self):
        """Check that constraints are imported as expected."""
        expected_module_constraint = {
            "domain": ["os"],
            "sudo": ["False"],
            "required": [],
            "perfimpact": ["False"],
            "software": [],
            "optional": [],
            "class": ["collect"],
            "parallelexclusive": [],
            "distro": ["alami", "ubuntu", "rhel", "suse"],
            "requires_ec2": ["False"]
        }

        self.assertDictEqual(self.module.constraint, expected_module_constraint)

    def test_module_title(self):
        """Test if module title set."""
        title = "sanity-check of basic module functions"
        self.assertEqual(self.module.title, title)

    def test_module_helpdoc(self):
        """Test that help doc is set."""
        helpdoc = "This module is an empty stub, used only in the development and qa of the\n" \
                  "interface between the main Automagic Diagnostics tool, and its modules.\n" \
                  "Requires sudo: False"
        self.assertEqual(self.module.helptext, helpdoc)

    def test_module_list(self):
        """Test that list returns formatted descripton."""
        response = "  ex                  collect   os           sanity-check of basic module functions" \
                   "                                       "
        self.assertEqual(self.module.list, response)

    def test_module_help(self):
        """Test that help returns formatted help message."""
        helptext = "This module is an empty stub, used only in the development and qa of the\n" \
                   "interface between the main Automagic Diagnostics tool, and its modules.\n" \
                   "Requires sudo: False"
        name = "ex"
        response = os.linesep.join(["{}:".format(name), helptext])
        self.assertEqual(self.module.help, response)

    def test_module_run_bash_unknown(self):
        """Check that run returns process output when running a BASH module."""
        my_opts = ec2rlcore.options.Options(subcommands=["run"])
        my_opts.global_args["perfimpact"] = True
        my_opts.per_module_args["ex"] = {"hello": True}
        my_opts.per_module_args["helloworld"] = {"hello": True}
        module_path = os.path.join(self.callpath, "test/modules/mod.d/ex.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        module_obj.run(options=my_opts)
        self.assertEqual("[UNKNOWN] log missing SUCCESS, FAILURE, or WARN message.",
                         module_obj.run_summary)
        self.assertEqual("UNKNOWN", module_obj.run_status)
        # Test path where this module doesn't have any per_module_args
        module_obj.run(options=my_opts)
        self.assertEqual("[UNKNOWN] log missing SUCCESS, FAILURE, or WARN message.",
                         module_obj.run_summary)
        self.assertEqual("UNKNOWN", module_obj.run_status)

    def test_module_run_bash_failure(self):
        """Check that run returns process output when running a BASH module."""
        my_opts = ec2rlcore.options.Options(subcommands=["run"])
        my_opts.global_args["perfimpact"] = True
        my_opts.per_module_args["ex"] = {"hello": True}
        my_opts.per_module_args["helloworld"] = {"hello": True}
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/ex_prints_failure.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        module_obj.run(options=my_opts)
        self.assertEqual("[FAILURE] module 'ex' can write a message to the main output",
                         module_obj.run_summary)
        self.assertEqual("FAILURE", module_obj.run_status)
        # Test path where this module doesn't have any per_module_args
        del my_opts.per_module_args["ex"]
        module_obj.run(options=my_opts)
        self.assertEqual("[FAILURE] module 'ex' can write a message to the main output",
                         module_obj.run_summary)
        self.assertEqual("FAILURE", module_obj.run_status)

    def test_module_run_bash_warn(self):
        """Check that run returns process output when running a BASH module."""
        my_opts = ec2rlcore.options.Options(subcommands=["run"])
        my_opts.global_args["perfimpact"] = True
        my_opts.per_module_args["ex"] = {"hello": True}
        my_opts.per_module_args["helloworld"] = {"hello": True}
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/ex_prints_warn.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        module_obj.run(options=my_opts)
        self.assertEqual("[WARN] module 'ex' can write a message to the main output",
                         module_obj.run_summary)
        self.assertEqual("WARN", module_obj.run_status)
        # Test path where this module doesn't have any per_module_args
        del my_opts.per_module_args["ex"]
        module_obj.run(options=my_opts)
        self.assertEqual("[WARN] module 'ex' can write a message to the main output",
                         module_obj.run_summary)
        self.assertEqual("WARN", module_obj.run_status)

    def test_module_run_success_details_single_line(self):
        """Check that single line details on a SUCCESS message return a matching single line of detail"""
        test_output = "[SUCCESS] This module ran correctly\n" \
                      "-- detail-line-one\n" \
                      "not-detail-line\n"
        expected_detail = ["-- detail-line-one"]
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_success_details_multiple_lines(self):
        """Check that multiple line details on a SUCCESS message returns matching multiple lines of detail"""
        test_output = "[SUCCESS] This module ran correctly\n" \
                      "-- detail-line-one\n" \
                      "-- detail-line-two\n" \
                      "not-detail-line\n"
        expected_detail = ["-- detail-line-one", "-- detail-line-two"]
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_success_details_no_lines(self):
        """Check that no details on a SUCCESS message returns empty list"""
        test_output = "[SUCCESS] This module ran correctly\n" \
                      "not-detail-line\n"
        expected_detail = []
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_success_details_malformed(self):
        """Check that skipping a line before details after SUCCESS message returns empty details list"""
        test_output = "[SUCCESS] This module ran correctly\n" \
                      "not-detail-line\n" \
                      "-- malformed-details-line"
        expected_detail = []
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_warn_details_single_line(self):
        """Check that single line details on a WARN message return a matching single line of detail"""
        test_output = "[WARN] This module ran with warnings\n" \
                      "-- detail-line-one\n" \
                      "not-detail-line\n"
        expected_detail = ["-- detail-line-one"]
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_warn_details_multiple_lines(self):
        """Check that multiple line details on a WARN message returns matching multiple lines of detail"""
        test_output = "[WARN] This module ran with warnings\n" \
                      "-- detail-line-one\n" \
                      "-- detail-line-two\n" \
                      "not-detail-line\n"
        expected_detail = ["-- detail-line-one", "-- detail-line-two"]
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_warn_details_no_lines(self):
        """Check that no details on a WARN message returns empty list"""
        test_output = "[WARN] This module ran with warnings\n"
        expected_detail = []
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_warn_details_malformed(self):
        """Check that skipping a line before details after WARN message returns empty details list"""
        test_output = "[WARN] This module ran with warnings\n" \
                      "not-detail-line\n" \
                      "-- malformed-details-line"
        expected_detail = []
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_failure_details_single_line(self):
        """Check that single line details on a FAILURE message return a matching single line of detail"""
        test_output = "[FAILURE] This module ran with failures\n" \
                      "-- detail-line-one\n" \
                      "not-detail-line\n"
        expected_detail = ["-- detail-line-one"]
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_failure_details_multiple_lines(self):
        """Check that multiple line details on a FAILURE message returns matching multiple lines of detail"""
        test_output = "[FAILURE] This module ran with failures\n" \
                      "-- detail-line-one\n" \
                      "-- detail-line-two\n" \
                      "not-detail-line\n"
        expected_detail = ["-- detail-line-one", "-- detail-line-two"]
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_failure_details_no_lines(self):
        """Check that no details on a FAILURE message returns empty list"""
        test_output = "[FAILURE] This module ran with failures\n" \
                      "not-detail-line\n"
        expected_detail = []
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_failure_details_malformed(self):
        """Check that skipping a line before details after FAILURE message returns empty details list"""
        test_output = "[FAILURE] This module ran with failures\n" \
                      "not-detail-line\n" \
                      "-- malformed-details-line"
        expected_detail = []
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_failure_details_malformed_skip_line(self):
        """Check that skipping a line between details after FAILURE message returns first line only"""
        test_output = "[FAILURE] This module ran with failures\n" \
                      "-- malformed-details-line-one\n" \
                      "not-detail-line\n" \
                      "-- malformed-details-line-two\n"

        expected_detail = ["-- malformed-details-line-one"]
        test_module = self.NonExecutingOutputModule("test-module")
        test_module.run(test_output)
        self.assertEqual(test_module.run_status_details, expected_detail)

    def test_module_run_python_global_args(self):
        """Check that run returns process output when running a Python module."""
        my_opts = ec2rlcore.options.Options(subcommands=["run"])
        my_opts.global_args["hello"] = "world"

        module_path = os.path.join(self.callpath, "test/modules/mod.d/helloworld.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        self.assertEqual("Hello world\n", module_obj.run(options=my_opts))

    def test_module_run_python_per_module_args(self):
        """Check that run returns process output when running a Python module."""
        my_opts = ec2rlcore.options.Options(subcommands=["run"])
        my_opts.per_module_args["helloworld"] = {"hello": "world"}

        module_path = os.path.join(self.callpath, "test/modules/mod.d/helloworld.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        self.assertEqual("Hello world\n", module_obj.run(options=my_opts))

    # Individual constraint tests
    def test_module_constraint_class(self):
        """Check that ModuleConstraintKeyError is raised when a module is missing the class constraint."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_class.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintKeyError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.module.get_module(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_class.yaml' missing required constraint 'class'.\n")

    def test_module_constraint_required(self):
        """Check that ModuleConstraintKeyError is raised when a module is missing the required constraint."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_required.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintKeyError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.module.get_module(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_required.yaml' missing required constraint 'required'.\n")

    def test_module_constraint_distro(self):
        """Check that ModuleConstraintKeyError is raised when a module is missing the distro constraint."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_distro.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintKeyError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.module.get_module(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_distro.yaml' missing required constraint 'distro'.\n")

    def test_module_constraint_domain(self):
        """Check that ModuleConstraintKeyError is raised when a module is missing the domain constraint."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_domain.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintKeyError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.module.get_module(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_domain.yaml' missing required constraint 'domain'.\n")

    def test_module_constraint_optional(self):
        """Check that ModuleConstraintKeyError is raised when a module is missing the optional constraint."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_optional.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintKeyError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.module.get_module(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_optional.yaml' missing required constraint 'optional'.\n")

    def test_module_constraint_parallelexclusive(self):
        """Check that ModuleConstraintKeyError is raised when a module is missing the parallelexclusive constraint."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_parallelexclusive.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintKeyError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.module.get_module(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_parallelexclusive.yaml' missing required constraint"
                         " 'parallelexclusive'.\n")

    def test_module_constraint_perfimpact(self):
        """Check that ModuleConstraintKeyError is raised when a module is missing the perfimpact constraint."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_perfimpact.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintKeyError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.module.get_module(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_perfimpact.yaml' missing required constraint 'perfimpact'.\n")

    def test_module_constraint_software(self):
        """Check that ModuleConstraintKeyError is raised when a module is missing the software constraint."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_software.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintKeyError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.module.get_module(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_software.yaml' missing required constraint 'software'.\n")

    def test_module_constraint_sudo(self):
        """Check that ModuleConstraintKeyError is raised when a module is missing the sudo constraint."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_sudo.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintKeyError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.module.get_module(module_path)
        self.assertEqual(self.output.getvalue(),
                         "Module parsing error: 'missing_sudo.yaml' missing required constraint 'sudo'.\n")

    def test_module_malformed_constraint(self):
        """
        Check that ModuleConstraintParseError is raised when a module has a typo in the constraint.
        In this scenario, the module is missing a colon after the constraint key name which causes yaml to fail to
        parse the file.
        """
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/malformed_constraint.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintParseError):
            ec2rlcore.module.get_module(module_path)

    # Module metadata tests

    def test_module_content_missing(self):
        """Check that ModuleConstraintParseError is raised when a module is missing its content."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_content.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintParseError):
            ec2rlcore.module.get_module(module_path)

    def test_module_help_missing(self):
        """Check that a ModuleConstraintParseError exception is raised when a module is missing its help message."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_help.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintParseError):
            ec2rlcore.module.get_module(module_path)

    def test_module_language_missing(self):
        """Check that ModuleConstraintParseError is raised when a module is missing its language."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_language.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintParseError):
            ec2rlcore.module.get_module(module_path)

    def test_module_name_missing(self):
        """Check that ModuleConstraintParseError is raised when a module is missing its name."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_name.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintParseError):
            ec2rlcore.module.get_module(module_path)

    def test_module_placement_missing(self):
        """Check that ModuleConstraintParseError is raised when a module is missing its placement."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_placement.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintParseError):
            ec2rlcore.module.get_module(module_path)

    def test_module_title_missing(self):
        """Check that ModuleConstraintParseError is raised when a module is missing its title."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_title.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintParseError):
            ec2rlcore.module.get_module(module_path)

    def test_module_package_missing(self):
        """Check that ModuleConstraintParseError is raised when a module is missing its package."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_package.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintParseError):
            ec2rlcore.module.get_module(module_path)

    def test_module_version_missing(self):
        """Check that a ModuleConstraintParseError exception is raised when a module is missing its version."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/missing_version.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleConstraintParseError):
            ec2rlcore.module.get_module(module_path)

    def test_module_unknown_placement(self):
        """Check that a ModuleUnknownPlacementError exception is raised when a module defines an unknown placement."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/unknown_placement.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleUnknownPlacementError):
            ec2rlcore.module.get_module(module_path)

    def test_module_unsupported_language_init(self):
        """
        Check that a UnsupportedLanguageError exception is raised when a module defines an unknown language during
        instantiation.
        """
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/unsupported_language.yaml")
        with self.assertRaises(ec2rlcore.module.ModuleUnsupportedLanguageError):
            ec2rlcore.module.get_module(module_path)

    def test_module_unsupported_language_run(self):
        """
        Check that a UnsupportedLanguageError exception is raised when a module defines an unknown language during
        run.
        """
        module_path = os.path.join(self.callpath, "test/modules/mod.d/ex.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)
        module_obj.language = "asdf"
        with self.assertRaises(ec2rlcore.module.ModuleUnsupportedLanguageError):
            module_obj.run()

    # Module execution tests
    def test_module_execution_failure(self):
        """Check that ModuleRunFailureError is raised when a module returns non-zero."""
        module_path = os.path.join(self.callpath, "test/modules/bad_mod.d/exits_nonzero.yaml")
        module_obj = ec2rlcore.module.get_module(module_path)

        self.assertRaises(ec2rlcore.module.ModuleRunFailureError, module_obj.run)

    # NonExecutingOutputModule overrides ec2rlcore.module.Module for testing
    # Used for module status details tests, minimal module needed to parse output
    # Other tests cover if Module._parse_output is run, so it is not necessary to
    #  create additional test module files for these tests.  The intended usage
    #  of this class is to test Module._parse_output itself.
    class NonExecutingOutputModule(ec2rlcore.module.Module):
        def __init__(self, name=None):
            self.name = name
            self.processoutput = ""
            self.run_status = ""
            self.run_summary = ""
            self.run_status_details = list()

        def run(self, output):
            self.processoutput = output
            self._parse_output(self.processoutput)
            return self.processoutput


if __name__ == "__main__":
    unittest.main()
