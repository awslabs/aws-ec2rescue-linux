# Copyright 2016-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

"""Unit tests for "constraint" module."""
import os
import sys
import unittest

import ec2rlcore.constraint


class TestConstraint(unittest.TestCase):
    """Testing class for "constraint" unit tests."""
    module_path = ""
    module = ""

    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    callpath = os.path.split(_callp)[0]

    def test_constraint_kwargs(self):
        """
        Check that instantiating a new Constraint object with keyword/arg pairs returns a Constraint object whose key
        list matches the keywords in the args.
        """
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        key_list = ["constraint1"]
        new_constraint = my_constraint.with_keys(key_list)
        new_constraint_key_list = [key for key in new_constraint]
        new_constraint_value_list = new_constraint["constraint1"]
        self.assertIsInstance(new_constraint, ec2rlcore.constraint.Constraint)
        # new_constraint should only contain one key, "constraint1"
        self.assertEqual(key_list, new_constraint_key_list)
        # new_constraint's "constraint1" key should have a value that is the list of a single string, "value1"
        self.assertEqual(["value1"], new_constraint_value_list)

    def test_constraint_with_keys(self):
        """Test that providing a keyward arg sets the constraint key/value pair."""
        my_constraint = ec2rlcore.constraint.Constraint(some_arg="some_value")
        self.assertTrue("some_arg" in my_constraint.keys())
        self.assertTrue("some_value" in my_constraint["some_arg"])

    def test_constraint_update_merge_values(self):
        """
        Check that when the update function is given a new dict with duplicate keys that the new values are still added.
        """
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_to_merge = {"constraint1": ["value3"]}
        my_constraint.update(dict_to_merge)
        self.assertEqual(my_constraint["constraint1"], ["value1", "value3"])

    def test_constraint_update_not_dict(self):
        """Check that TypeError is raised when the update function is given a non-dict data structure."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        list_to_merge = ["value3"]
        self.assertRaises(TypeError, my_constraint.update, list_to_merge)

    def test_constraint_update_none_value(self):
        """Check that a Constraint adds a new key when given a key/value pair where the value is None."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_to_merge = {"constraint3": None}
        my_constraint.update(dict_to_merge)
        self.assertTrue("constraint3" in my_constraint.keys())

    def test_constraint_update_empty_dict(self):
        """Check that a Constraint is not modified when updating with an empty dict."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_to_merge = {}
        my_constraint.update(dict_to_merge)
        self.assertEqual({"constraint1": ["value1"], "constraint2": ["value2"]}, my_constraint)

    def test_constraint_setitem_noniterable(self):
        """Check that a Constraint is not modified when the value is not an iterable."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        my_constraint["constraint1"] = 1234
        self.assertEqual({"constraint1": ["value1"], "constraint2": ["value2"]}, my_constraint)

    def test_constraint_update_dict_value(self):
        """Check that a Constraint adds new keys when given a dict containing a dict."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_to_merge = {"new_constraint": {"constraint1": ["value3"]}}
        my_constraint.update(dict_to_merge)
        self.assertTrue("value3" in my_constraint["constraint1"])

    def test_constraint_update_set(self):
        """Check that a Constraint adds new keys when given a dict containing a set value."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_to_merge = {"constraint1": {"value3", "value4"}}
        my_constraint.update(dict_to_merge)
        self.assertTrue("value3" in my_constraint["constraint1"])
        self.assertTrue("value4" in my_constraint["constraint1"])

    def test_constraint_update_tuple(self):
        """Check that a Constraint adds new keys when given a dict containing a tuple value."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_to_merge = {"constraint1": ("value3", "value4")}
        my_constraint.update(dict_to_merge)
        self.assertTrue("value3" in my_constraint["constraint1"])
        self.assertTrue("value4" in my_constraint["constraint1"])

    def test_constraint_contains_dict(self):
        """Check that checking for presense of dict key/value pairs works with a Constraint object."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_to_check = {"constraint1": "value2"}
        my_constraint.__contains__(dict_to_check)
        self.assertTrue(my_constraint.__contains__, dict_to_check)

    def test_constraint_contains_dict_with_list_value(self):
        """
        Check that when checking for presense of dict key/value pairs the Constraint checks all values in a
        key's list value.
        """
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_with_list_to_check = {"constraint1": ["value2"]}
        my_constraint.__contains__(dict_with_list_to_check)
        self.assertTrue(my_constraint.__contains__, dict_with_list_to_check)

    def test_constraint_contains_dict_with_tuple_value(self):
        """
        Check that when checking for presense of dict key/value pairs the Constraint checks all values in a
        key's tuple value.
        """
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_with_tuple_to_check = {"constraint1": ("value1", "value2")}
        my_constraint.__contains__(dict_with_tuple_to_check)
        self.assertTrue(my_constraint.__contains__, dict_with_tuple_to_check)

    def test_constraint_contains_tuple_of_str(self):
        """Check that checking for presense of a tuple of strings returns False."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        tuple_to_check = ("value1", "value2")
        self.assertFalse(my_constraint.__contains__(tuple_to_check))

    def test_constraint_contains_list_of_str(self):
        """Check that checking for presense of a list of strings returns False."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        list_to_check = ["value1", "value2"]
        self.assertFalse(my_constraint.__contains__(list_to_check))

    def test_constraint_contains_list_of_dict(self):
        """
        Check that checking for presense of a list containing a dict whose key/value pairs
        are contained in the Constraint returns True.
        """
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        list_to_check = [{"constraint2": "value2"}]
        self.assertTrue(my_constraint.__contains__(list_to_check))

    def test_constraint_contains_dict_not_found(self):
        """
        Check that checking for presense of dict key/value pairs not in a Constraint object correctly returns False.
        """
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        dict_to_check = {"constraint9": ["value9"]}
        self.assertFalse(my_constraint.__contains__(dict_to_check))

    def test_constraint_setitem_str(self):
        """Check that setting a Constraint key's value using a string arg succeeds."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        my_constraint.__setitem__("constraint1", "value3")
        self.assertTrue("value3" in my_constraint["constraint1"])

    def test_constraint_setitem_dict(self):
        """Check that setting a Constraint key's value using a dict arg succeeds."""
        my_constraint = ec2rlcore.constraint.Constraint(constraint1="value1", constraint2="value2")
        my_constraint.__setitem__("constraint1", {"constraint1", "value3"})
        self.assertTrue("value3" in my_constraint["constraint1"])

if __name__ == "__main__":
    unittest.main()
