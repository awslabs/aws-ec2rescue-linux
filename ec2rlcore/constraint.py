# Copyright 2016-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at

#     http://aws.amazon.com/apache2.0/


# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""
Constraint module

Functions:
    None

Classes:
    Constraint: dict-like object to hold requirements as key:value pairs

Exceptions:
    None
"""

from __future__ import print_function
import collections
import copy

from ec2rlcore.logutil import LogUtil


class Constraint(dict):
    """
    Holds parsed module metadata and command line arguments

    Attributes:

    Methods:
        without_keys: return a Constraint with all keys except those specified
        with_keys: return a Constraint with only the specified keys
        update: merge the specified dict into the Constraint's existing key:value pairs
        __setitem__: add or update the key:value pair using the specified values
        __contains__: return whether the Constraint contains the specified object or value

    """
    def __init__(self, arg=None, **kwargs):
        """
        Perform initial configuration of the object.

        Parameters:
            arg: a dict of key:value pairs
            kwargs: optional key:value pairs where the kwarg == key and arg value == value
        """
        self.logger = LogUtil.get_root_logger()
        self.logger.debug("constraint.Constraint.__init__({}, {})".format(arg, kwargs))
        super(Constraint, self).__init__(self)
        if arg and isinstance(arg, dict):
            self.logger.debug("arg is dict")
            self.update(arg)
        if kwargs:
            self.update(kwargs)
        self.logger.debug("resulting constraint dict =  {}".format(self))

    def without_keys(self, keylist):
        """Return an instance of Constraint with all keys except those in the keylist parameter"""
        self.logger.debug("constraint.Constraint.without_keys()")
        assert isinstance(keylist, (list, tuple, set))
        constraint_dict = {}
        for key in self:
            if key not in keylist:
                constraint_dict[key] = self[key]
        return Constraint(constraint_dict)

    def with_keys(self, keylist):
        """Return an instance of Constraint with only the keys in the keylist parameter"""
        self.logger.debug("constraint.Constraint.with_keys()")
        assert isinstance(keylist, (list, tuple, set))
        constraint_dict = {}
        for key in self:
            if key in keylist:
                constraint_dict[key] = self[key]
        return Constraint(constraint_dict)

    def update(self, other):
        """
        Recurse through the "other" dict and update existing key:value pairs and add missing new:value pairs

        Parameters:
            other (dict): the dict whose key:value pairs will be added to the Constraint

        Returns:
            True (bool)
        """
        def merge_values(key):
            """
            Given a key, merge other's key's values with the constraint's key's values

            Parameters:
                key (str): the key whose values should be merged

            Returns:
                None
            """
            self.logger.debug("merge existing '{}'".format(key))
            for item in other[key]:
                # Only add the item if it is not a duplicate
                if item not in self[key]:
                    self[key].append(item)

        self.logger.debug("constraint.Constraint.update({})".format(other))
        # Verify "other" is a dict
        if not isinstance(other, dict):
            self.logger.debug("TypeError: expected dict")
            raise TypeError("{0!r} is not a dict or Constraint mapping".format(other))
        for okey in other.keys():
            # Recursive cases. Recurse another level to find key:value pairs.
            # Case: value is empty. Recurse with an empty list.
            if other[okey] is None:
                self.logger.debug("None case: recursing on '{}'".format(okey))
                self.update({okey: []})
            # Case: value is a dict
            elif type(other[okey]) == dict:
                self.logger.debug("is dict case: recursing on '{}'".format(okey))
                self.update(other[okey])
            # Case: value is a set, tuple, or str. Recurse with a list created from the value.
            elif isinstance(other[okey], (set, tuple)):
                self.logger.debug("isinstance case: recursing on '{}'".format(okey))
                self.update({okey: list(other[okey])})
            elif isinstance(other[okey], str):
                self.logger.debug("isinstance case: recursing on '{}'".format(okey))
                # If the string is a space-delimited sequence of values then split the string and recurse on the list
                if " " in other[okey]:
                    self.update({okey: other[okey].split()})
                # If the okey value is an empty string then the resultant value should be an empty list
                elif not other[okey]:
                    self.update({okey: []})
                else:
                    self.update({okey: [other[okey]]})
            # Base case: value is a list. Merge in the list or set the list as the key's value.
            else:
                # Case: if the key exists in the dict then merge in the values in the list
                if okey in self:
                    merge_values(okey)
                # Case: if the key doesn't exist in the dict then set the list as the key's value
                else:
                    self.logger.debug("setting new '{}'".format(okey))
                    self[okey] = copy.deepcopy(other[okey])
        return True

    def __setitem__(self, key, val):
        """
        Update/set the Constraint key:value pair from the given parameter values. val should normally be a list.
        If val is a list, check the value

        Parameters:
            key (str): key representing the constraint name (e.g. "distro")
            val: value representing the constraint value or values (e.g. "alami")

        Returns:
            True (bool)
        """
        # self.logger.debug("constraint.Constraint.__setitem__({}, {})".format(key, val))
        if not isinstance(val, list):
            if isinstance(val, str):
                self.__setitem__(key, [val])
            elif isinstance(val, collections.Iterable):
                self.__setitem__(key, list(val))
        else:
            if key in self:
                del self[key]
            dict.__setitem__(self, key, val)
        return True

    def __contains__(self, other):
        """
        Return whether the Constraint contains a key, list of keys, or a dictionary.

        Parameters:
            other: the object to check whether is present in the Constraint

        Returns:
            rv (bool): whether the value is contained in the Constraint
        """
        rv = False

        def rebool(item_to_search):
            """Search item_to_search for False and return False if found else return the truthiness of x.

            Parameters:
                item_to_search: an iterable to be searched

            Returns:
                (bool): False if False is in item_to_search else the value of truthiness of item_to_search
            """
            return False if False in item_to_search else bool(item_to_search)

        if isinstance(other, (list, tuple)):
            rv = [self.__contains__(i) for i in other]
            rv = rebool(rv)

        elif not isinstance(other, dict):
            rv = dict.__contains__(self, other)

        # Equivalent to "elif isinstance(other, dict):"
        else:
            for okey in other.keys():
                if isinstance(other[okey], (list, tuple)):
                    rv = [self.__contains__(dict([(okey, v)])) for v in other[okey]]
                    rv = rebool(rv)
                elif okey in self:
                    rv = other[okey] in self[okey]
                else:
                    rv = False
        return rv
