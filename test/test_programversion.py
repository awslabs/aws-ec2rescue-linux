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

"""Unit tests for "programversion" module."""
import unittest

import ec2rlcore.programversion


class TestProgramVersion(unittest.TestCase):
    """Testing class for "programversion" unit tests."""

    def test_programversion_invalid_version_string(self):
        """Test that a VersionParsingError is raised when an invalid version string is provided."""
        invalid_version_string = "asdf"
        with self.assertRaises(ec2rlcore.programversion.ProgramVersionParsingError):
            ec2rlcore.programversion.ProgramVersion(invalid_version_string)

    def test_programversion_invalid_version_string_newline(self):
        """Test that a VersionParsingError is raised when a valid version string with a trailing newline is provided."""
        invalid_version_string = "1.0.0rc1\n"
        with self.assertRaises(ec2rlcore.programversion.ProgramVersionParsingError):
            ec2rlcore.programversion.ProgramVersion(invalid_version_string)

    def test_programversion_major_integer_equality(self):
        """Test that equality tests function normally when the major value includes leading zeroes."""
        version_string = "1.0.0b6"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        self.assertTrue(version_object.major == "1")
        self.assertTrue(int(version_object.major) == 1)
        self.assertTrue(version_object == ec2rlcore.programversion.ProgramVersion("1.0.0b6"))

    def test_programversion_minor_integer_equality(self):
        """Test that equality tests function normally when the minor value includes leading zeroes."""
        version_string = "1.0.0b6"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        self.assertTrue(version_object.minor == "0")
        self.assertTrue(int(version_object.minor) == 0)
        self.assertTrue(version_object == ec2rlcore.programversion.ProgramVersion("1.0.0b6"))

    def test_programversion_micro_integer_equality(self):
        """Test that equality tests function normally when the micro value includes leading zeroes."""
        version_string = "1.0.0b6"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        self.assertTrue(version_object.pre_release == "6")
        self.assertTrue(int(version_object.pre_release) == 6)
        self.assertTrue(version_object == ec2rlcore.programversion.ProgramVersion("1.0.0b6"))

    def test_programversion_release_equality(self):
        """Test that equality tests evaluate the release version correctly."""
        version_string = "1.0.0b6"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        self.assertTrue(version_object.release_numerical == 2)
        self.assertTrue(version_object == ec2rlcore.programversion.ProgramVersion("1.0.0b6"))

    def test_programversion_comparison_major(self):
        """Test that equality tests correctly evaluate objects with different major versions."""
        version_string = "2.0.0rc1"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        other_version_string = "1.0.0rc1"
        other_version_object = ec2rlcore.programversion.ProgramVersion(other_version_string)
        self.assertTrue(other_version_object < version_object)
        self.assertTrue(other_version_object != version_object)

    def test_programversion_comparison_minor(self):
        """Test that equality tests correctly evaluate objects with different minor versions."""
        version_string = "1.0.0b6"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        other_version_string = "1.0.1b6"
        other_version_object = ec2rlcore.programversion.ProgramVersion(other_version_string)
        self.assertTrue(other_version_object > version_object)
        self.assertTrue(other_version_object != version_object)

    def test_programversion_comparison_micro(self):
        """Test that equality tests correctly evaluate objects with different micro versions."""
        version_string = "1.0.0b7"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        other_version_string = "1.0.0b6"
        other_version_object = ec2rlcore.programversion.ProgramVersion(other_version_string)
        self.assertTrue(other_version_object < version_object)
        self.assertTrue(other_version_object != version_object)

    def test_programversion_comparison_release_alpha_beta(self):
        """Test that equality tests correctly evaluate objects with different release types."""
        version_string = "1.0.0a6"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        other_version_string = "1.0.0b6"
        other_version_object = ec2rlcore.programversion.ProgramVersion(other_version_string)
        self.assertTrue(other_version_object > version_object)
        self.assertTrue(other_version_object != version_object)

    def test_programversion_comparison_release_beta_candidate(self):
        """Test that equality tests correctly evaluate objects with different release types."""
        version_string = "1.0.0b6"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        other_version_string = "1.0.0rc6"
        other_version_object = ec2rlcore.programversion.ProgramVersion(other_version_string)
        self.assertTrue(other_version_object > version_object)
        self.assertTrue(other_version_object != version_object)

    def test_programversion_comparison_release_candidate_release(self):
        """Test that equality tests correctly evaluate objects with different release types."""
        version_string = "1.0.0rc6"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        other_version_string = "1.0.0"
        other_version_object = ec2rlcore.programversion.ProgramVersion(other_version_string)
        self.assertTrue(other_version_object > version_object)
        self.assertTrue(other_version_object != version_object)

    def test_programversion_comparison_release_alpha_release(self):
        """Test that equality tests correctly evaluate objects with different release types."""
        version_string = "1.0.0a6"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        other_version_string = "1.0.0"
        other_version_object = ec2rlcore.programversion.ProgramVersion(other_version_string)
        self.assertTrue(other_version_object > version_object)
        self.assertTrue(other_version_object != version_object)

    def test_programversion_comparison_different_object_type_eq(self):
        """
        Test that InvalidComparisonError is raised when a ProgramVersion is compared for equality with another 
        object of a different type using the '==' operator.
        """
        test_dict = {"version": "1.0.0"}
        version_string = "1.0.0"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        with self.assertRaises(ec2rlcore.programversion.ProgramVersionInvalidComparisonError):
            bool(test_dict == version_object)

    def test_programversion_comparison_different_object_type_ne(self):
        """
        Test that InvalidComparisonError is raised when a ProgramVersion is compared for equality with another 
        object of a different type using the '!=' operator.
        """
        test_dict = {"version": "1.0.0"}
        version_string = "1.0.0"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        with self.assertRaises(ec2rlcore.programversion.ProgramVersionInvalidComparisonError):
            bool(test_dict != version_object)

    def test_programversion_comparison_different_object_type_lt(self):
        """
        Test that InvalidComparisonError is raised when a ProgramVersion is compared for equality with another 
        object of a different type using the '>' operator.
        """
        test_dict = {"version": "1.0.0"}
        version_string = "1.0.0"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        with self.assertRaises(ec2rlcore.programversion.ProgramVersionInvalidComparisonError):
            bool(test_dict > version_object)

    def test_programversion_print_release(self):
        """
        Test that ProgramVersion.__str__ returns the expected string representation of the ProgramVersion whose
        release type is 'release'.
        """
        version_string = "1.0.0"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        self.assertEqual(str(version_object), version_string)

    def test_programversion_print_beta(self):
        """
        Test that ProgramVersion.__str__ returns the expected string representation of the ProgramVersion whose
        release type is 'beta'.
        """
        version_string = "1.0.0b1"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        self.assertEqual(str(version_object), version_string)

    def test_programversion_print_alpha(self):
        """
        Test that ProgramVersion.__str__ returns the expected string representation of the ProgramVersion whose
        release type is 'alpha'.
        """
        version_string = "1.0.0a1"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        self.assertEqual(str(version_object), version_string)

    def test_programversion_print_rc(self):
        """
        Test that ProgramVersion.__str__ returns the expected string representation of the ProgramVersion whose
        release type is 'candidate'.
        """
        version_string = "1.0.0rc1"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        self.assertEqual(str(version_object), version_string)

    def test_programversion_repr(self):
        """
        Test that ProgramVersion.__repr__ returns the expected string representations of the ProgramVersion instances.
        """
        version_object = ec2rlcore.programversion.ProgramVersion("1.0.0rc1")
        self.assertEqual(repr(version_object), 'ProgramVersion("1.0.0rc1")')
        version_object = ec2rlcore.programversion.ProgramVersion("1.0.0")
        self.assertEqual(repr(version_object), 'ProgramVersion("1.0.0")')

    def test_programversion_len(self):
        """
        Test that ProgramVersion works with the Python built-in len(). The length of the string representation is
        expected to be returned..
        """
        version_string = "1.0.0rc1"
        version_object = ec2rlcore.programversion.ProgramVersion(version_string)
        self.assertEqual(len(version_object), 8)
