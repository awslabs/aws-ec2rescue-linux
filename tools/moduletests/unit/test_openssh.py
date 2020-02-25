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

"""Unit tests for "openssh" module."""

import errno
import os
import stat
import subprocess
import sys
import unittest

try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib

import botocore
import mock
import responses

import moduletests.src.openssh


class TestSSH(unittest.TestCase):
    """SSH tests."""
    metadata_url = "http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key"
    mock_counter = 0
    maxDiff = None

    def get_mocked_stat(*args, **kwargs):
        TestSSH.mock_counter += 1
        return mock.Mock(st_dev=TestSSH.mock_counter, st_ino=TestSSH.mock_counter)

    @staticmethod
    def return_true(*args, **kwargs):
        return True

    @staticmethod
    def return_false(*args, **kwargs):
        return False

    def setUp(self):
        self.path = moduletests.src.openssh.Path(
            path_str="/tmp", e_uid=0, e_gid=0, v_bitmask=(stat.S_IWGRP | stat.S_IWOTH))

        self.problem = moduletests.src.openssh.Problem(state="UNCHECKED",
                                                             item_type="Config",
                                                             item=self.path,
                                                             value=None,
                                                             value_str="Missing",
                                                             info_msg="Found bad lines in configuration file",
                                                             check=self.return_true,
                                                             check_msg="validity of configuration",
                                                             fix_msg=None,
                                                             fix=self.return_true)
        moduletests.src.openssh.Problem.CONFIG_DICT = {"HOSTKEYS": [],
                                                       "AUTH_KEYS": {"absolute": ["/one/two/three/file1",
                                                                                  "/usr/secrets/file2"],
                                                                     "relative": [".ssh/authorized_keys",
                                                                                  ".keyfile1"]},
                                                       "CONFIG_PATH": "/etc/ssh/sshd_config",
                                                       "CONFIG_DICT": dict(),
                                                       "REMEDIATE": False,
                                                       "INJECT_KEY": False,
                                                       "INJECT_KEY_ONLY": False,
                                                       "CREATE_NEW_KEYS": False,
                                                       "NEW_KEY": None,
                                                       "NOT_AN_INSTANCE": False,
                                                       "BACKED_FILES": dict(),
                                                       "BACKUP_DIR": "/var/tmp/ec2rl_ssh/backup",
                                                       "LOG_DIR": "/var/tmp/ec2rl_ssh",
                                                       "PRIV_SEP_DIR": "/var/empty/sshd",
                                                       "ALL_SET_BITMASK": 0b111111111111111,
                                                       "G_O_WRITE_CHECKING_BITMASK": stat.S_IWGRP | stat.S_IWOTH,
                                                       "G_O_ALL_CHECKING_BITMASK": stat.S_IRWXG | stat.S_IRWXO}
        self.vertex = moduletests.src.openssh.Vertex("example vertex", [1, 2, 3])
        self.dag = moduletests.src.openssh.DirectedAcyclicGraph()

    def tearDown(self):
        self.path = None
        self.problem = None
        self.vertex = None
        self.dag = None

    def test_ssh_vertex_instantiation(self):
        """Test instantiation of a Vertex."""
        self.assertEqual(self.vertex.visited, False)
        self.assertEqual(self.vertex.continuable, True)
        self.assertTrue(isinstance(self.vertex.successors, list))
        self.assertEqual(len(self.vertex.successors), 0)
        self.assertEqual(self.vertex.in_degree, 0)
        self.assertEqual(self.vertex.label, "example vertex")
        self.assertEqual(self.vertex.data, [1, 2, 3])

    def test_ssh_vertex_add_successor(self):
        self.assertTrue(self.vertex.add_successor(1))
        self.assertFalse(self.vertex.add_successor(1))

    def test_ssh_vertex_remove_successor(self):
        self.vertex.add_successor(1)
        self.assertTrue(self.vertex.remove_successor(1))
        self.assertFalse(self.vertex.remove_successor(1))

    def test_ssh_vertex_str(self):
        self.assertEqual(self.vertex.__str__(), "example vertex")

    def test_ssh_vertex_repr(self):
        self.assertEqual(self.vertex.__repr__(), "Vertex(label='example vertex', data=[1, 2, 3])")

    def test_ssh_vertex_iter(self):
        self.assertTrue(self.vertex.add_successor(1))
        self.assertTrue(self.vertex.add_successor(2))
        self.assertTrue(iter(self.vertex))

    def test_ssh_path_instantiation(self):
        self.assertEqual(self.path.path_str, "/tmp")
        self.assertEqual(self.path.e_mode, None)
        self.assertEqual(self.path.e_uid, 0)
        self.assertEqual(self.path.e_gid, 0)
        self.assertEqual(self.path.v_bitmask, stat.S_IWGRP | stat.S_IWOTH)

    @mock.patch("os.stat")
    def test_ssh_path_property_mode(self, os_mock):
        os_mock.return_value = mock.Mock(st_mode=666)
        self.assertEqual(self.path.mode, 666)
        self.assertTrue(os_mock.called)

    @mock.patch("os.stat")
    def test_ssh_path_property_uid(self, os_mock):
        os_mock.return_value = mock.Mock(st_uid=666)
        self.assertEqual(self.path.uid, 666)
        self.assertTrue(os_mock.called)

    @mock.patch("os.stat")
    def test_ssh_path_property_gid(self, os_mock):
        os_mock.return_value = mock.Mock(st_gid=666)
        self.assertEqual(self.path.gid, 666)
        self.assertTrue(os_mock.called)

    @mock.patch("os.path.isdir", side_effect=[False, True])
    def test_ssh_path_property_isdir(self, os_mock):
        self.assertFalse(self.path.isdir)
        self.assertTrue(self.path.isdir)
        self.assertTrue(os_mock.called)

    @mock.patch("os.path.isfile", side_effect=[False, True])
    def test_ssh_path_property_isfile(self, os_mock):
        self.assertFalse(self.path.isfile)
        self.assertTrue(self.path.isfile)
        self.assertTrue(os_mock.called)

    def test_ssh_path_str(self):
        self.assertEqual(str(self.path), "/tmp")

    def test_ssh_path_repr(self):
        self.assertEqual(repr(self.path), "Path(path_str=/tmp, e_mode=None, e_uid=0, e_gid=0 v_bitmask={})".format(
            stat.S_IWGRP | stat.S_IWOTH))

    def test_ssh_dag_instantiation(self):
        self.assertEqual(len(self.dag), 0)

    def test_ssh_dag_add_vertex(self):
        self.assertTrue(self.dag.add_vertex(self.vertex))
        self.assertTrue(self.vertex.label in self.dag.vertices.keys())
        self.assertEqual(self.dag.vertices[self.vertex.label], self.vertex)
        self.assertEqual(len(self.dag), 1)
        # Adding a second time should fail
        self.assertFalse(self.dag.add_vertex(self.vertex))
        self.assertEqual(len(self.dag), 1)

    def test_ssh_dag_add_edge(self):
        new_vert = moduletests.src.openssh.Vertex("test", [])
        self.dag.add_vertex(new_vert)
        # One Vertex is not in the DAG
        self.assertFalse(self.dag.add_edge(new_vert.label, self.vertex.label))
        self.dag.add_vertex(self.vertex)
        # Creates a loop
        self.assertFalse(self.dag.add_edge(new_vert.label, new_vert.label))
        # Valid
        self.assertTrue(self.dag.add_edge(new_vert.label, self.vertex.label))
        # Creates a cycle
        self.assertFalse(self.dag.add_edge(self.vertex.label, new_vert.label))

    def test_ssh_dag_remove_vertex(self):
        # Add a Vertex
        self.assertTrue(self.dag.add_vertex(self.vertex))
        self.assertEqual(len(self.dag), 1)
        # Add a second Vertex
        new_vert = moduletests.src.openssh.Vertex("test", [])
        self.assertTrue(self.dag.add_vertex(new_vert))
        self.assertEqual(len(self.dag), 2)
        # Remove the original Vertex
        self.assertTrue(self.dag.remove_vertex(self.vertex.label))
        self.assertEqual(len(self.dag), 1)
        # Removing the Vertex when not in the DAG should fail
        self.assertFalse(self.dag.remove_vertex(self.vertex.label))
        # Re-add the original Vertex and add an edge so the remove successors branch can be tested
        self.assertTrue(self.dag.add_vertex(self.vertex))
        self.dag.add_edge(new_vert.label, self.vertex.label)
        self.assertTrue(self.dag.remove_vertex(self.vertex.label))
        self.assertTrue(self.vertex.label not in new_vert.successors)

    def test_ssh_dag_remove_edge(self):
        self.dag.add_vertex(self.vertex)
        new_vert = moduletests.src.openssh.Vertex("test", [])
        self.dag.add_vertex(new_vert)
        self.dag.add_edge(new_vert.label, self.vertex.label)
        self.assertTrue(self.vertex.label in new_vert.successors)
        self.assertTrue(self.dag.remove_edge(new_vert.label, self.vertex.label))
        self.assertFalse(self.vertex.label in new_vert.successors)
        self.assertFalse(self.dag.remove_edge(new_vert.label, new_vert.label))
        self.dag.remove_vertex(self.vertex.label)
        self.assertFalse(self.dag.remove_edge(new_vert.label, self.vertex.label))

    def test_ssh_dag_str(self):
        new_vert = moduletests.src.openssh.Vertex("test", [1])
        self.dag.add_vertex(new_vert)
        self.dag.add_vertex(self.vertex)
        self.dag.add_edge(new_vert.label, self.vertex.label)
        self.assertEqual(str(self.dag), "example vertex : \ntest : example vertex")

    def test_ssh_dag_topo_sort(self):
        new_vert_one = moduletests.src.openssh.Vertex("testone", [1])
        new_vert_two = moduletests.src.openssh.Vertex("testtwo", [2])
        self.dag.add_vertex(new_vert_one)
        self.dag.add_vertex(new_vert_two)
        self.dag.add_vertex(self.vertex)
        self.dag.add_edge(new_vert_one.label, self.vertex.label)
        self.dag.add_edge(new_vert_two.label, self.vertex.label)
        self.assertEqual(self.dag.topological_sort(), [new_vert_one.label, new_vert_two.label, self.vertex.label])

    def test_ssh_dag_topo_solve(self):
        problem_npf = moduletests.src.openssh.Problem(state="UNCHECKED",
                                                            item_type="Config",
                                                            item=self.path,
                                                            value=None,
                                                            value_str="Missing",
                                                            info_msg="NPF problem",
                                                            check=self.return_false,
                                                            check_msg="NPF problem",
                                                            fix_msg="No problem found",
                                                            fix=self.return_true)
        problem_fix_failed = moduletests.src.openssh.Problem(state="UNCHECKED",
                                                                   item_type="Config",
                                                                   item=self.path,
                                                                   value=None,
                                                                   value_str="Missing",
                                                                   info_msg="Fix failed problem",
                                                                   check=self.return_true,
                                                                   check_msg="Fix failed problem",
                                                                   fix_msg="Can not be fixed",
                                                                   fix=self.return_false)
        problem_fixed = moduletests.src.openssh.Problem(state="UNCHECKED",
                                                              item_type="Config",
                                                              item=self.path,
                                                              value=None,
                                                              value_str="Missing",
                                                              info_msg="Fixed problem",
                                                              check=self.return_true,
                                                              check_msg="Fixed problem",
                                                              fix_msg="Can be fixed",
                                                              fix=self.return_true)

        new_vert_a = moduletests.src.openssh.Vertex("a", problem_npf)
        new_vert_b = moduletests.src.openssh.Vertex("b", problem_fix_failed)
        new_vert_c = moduletests.src.openssh.Vertex("c", problem_fixed)
        self.dag.add_vertex(new_vert_a)
        self.dag.add_vertex(new_vert_b)
        self.dag.add_vertex(new_vert_c)
        with contextlib.redirect_stdout(StringIO()):
            self.dag.add_edge(new_vert_a.label, new_vert_b.label)
            self.dag.add_edge(new_vert_b.label, new_vert_c.label)
            self.assertEqual(self.dag.topological_solve(remediate=True), [new_vert_a, new_vert_b])
            self.assertEqual(self.dag.topological_solve(remediate=False), [new_vert_a, new_vert_b])

            self.dag.remove_edge(new_vert_b.label, new_vert_c.label)
            self.dag.add_edge(new_vert_a.label, new_vert_c.label)
            self.assertEqual(self.dag.topological_solve(remediate=True), [new_vert_a, new_vert_b, new_vert_c])
            self.assertEqual(self.dag.topological_solve(remediate=False), [new_vert_a, new_vert_b, new_vert_c])

            self.dag.remove_edge(new_vert_a.label, new_vert_c.label)
            self.dag.remove_edge(new_vert_a.label, new_vert_b.label)
            self.dag.add_edge(new_vert_a.label, new_vert_b.label)
            self.dag.add_edge(new_vert_c.label, new_vert_b.label)
            self.assertEqual(self.dag.topological_solve(remediate=True), [new_vert_a, new_vert_c, new_vert_b])
            self.assertEqual(self.dag.topological_solve(remediate=False), [new_vert_a, new_vert_c])

    def test_ssh_dag_search_bfs(self):
        new_vert_a = moduletests.src.openssh.Vertex("a", [])
        new_vert_b = moduletests.src.openssh.Vertex("b", [])
        new_vert_c = moduletests.src.openssh.Vertex("c", [])
        new_vert_d = moduletests.src.openssh.Vertex("d", [])
        new_vert_e = moduletests.src.openssh.Vertex("e", [])
        new_vert_f = moduletests.src.openssh.Vertex("f", [])
        self.dag.add_vertex(self.vertex)
        self.dag.add_vertex(new_vert_a)
        self.dag.add_vertex(new_vert_b)
        self.dag.add_vertex(new_vert_c)
        self.dag.add_vertex(new_vert_d)
        self.dag.add_vertex(new_vert_e)
        self.dag.add_vertex(new_vert_f)
        self.dag.add_edge(self.vertex.label, new_vert_a.label)
        self.dag.add_edge(self.vertex.label, new_vert_b.label)
        self.dag.add_edge(new_vert_a.label, new_vert_c.label)
        self.dag.add_edge(new_vert_b.label, new_vert_e.label)
        self.dag.add_edge(new_vert_b.label, new_vert_d.label)
        self.dag.add_edge(new_vert_b.label, new_vert_f.label)
        self.dag.add_edge(new_vert_d.label, new_vert_f.label)

        # The ordering is predictable since an OrderedDict is used
        self.assertEqual(self.dag.search(mode="breadth"), ["example vertex", "a", "b", "c", "e", "d", "f"])

    def test_ssh_dag_search_dfs(self):
        new_vert_a = moduletests.src.openssh.Vertex("a", [])
        new_vert_b = moduletests.src.openssh.Vertex("b", [])
        new_vert_c = moduletests.src.openssh.Vertex("c", [])
        new_vert_d = moduletests.src.openssh.Vertex("d", [])
        new_vert_e = moduletests.src.openssh.Vertex("e", [])
        self.dag.add_vertex(self.vertex)
        self.dag.add_vertex(new_vert_a)
        self.dag.add_vertex(new_vert_b)
        self.dag.add_vertex(new_vert_c)
        self.dag.add_vertex(new_vert_d)
        self.dag.add_vertex(new_vert_e)
        self.dag.add_edge(self.vertex.label, new_vert_a.label)
        self.dag.add_edge(self.vertex.label, new_vert_b.label)
        self.dag.add_edge(new_vert_a.label, new_vert_c.label)
        self.dag.add_edge(new_vert_b.label, new_vert_e.label)
        self.dag.add_edge(new_vert_b.label, new_vert_d.label)
        # The ordering is predictable since an OrderedDict is used
        self.assertEqual(self.dag.search(mode="depth"), ["example vertex", "b", "d", "e", "a", "c"])

    def test_ssh_dag_search_invalid_mode(self):
        self.assertFalse(self.dag.search(mode="invalid"))

    def test_ssh_dag__search_from_vert_invalid_start(self):
        self.dag.add_vertex(self.vertex)
        self.assertFalse(self.dag._search_from_vert(mode="breadth", start="vertex", visited=set()))

    def test_ssh_dag__search_from_vert_invalid_visited(self):
        self.dag.add_vertex(self.vertex)
        self.assertFalse(self.dag._search_from_vert(mode="breadth", start=self.vertex, visited=dict()))

    def test_ssh_dag__search_from_vert_invalid_mode(self):
        self.dag.add_vertex(self.vertex)
        self.assertFalse(self.dag._search_from_vert(mode="invalid", start=self.vertex, visited=set()))

    @mock.patch("moduletests.src.openssh.get_config_file_path", side_effect=["test"])
    @mock.patch("moduletests.src.openssh.parse_configuration",
                side_effect=[{"HostKey": ["/etc/ssh/ssh_host_rsa_key"],
                              "AuthorizedKeysFile": [".ssh/authorized_keys"]}])
    def test_ssh_problem_setup_config_vars_relative_auth_keys(self, parse_mock, get_path_mock):
        moduletests.src.openssh.Problem.setup_config_vars()
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["CONFIG_PATH"], "test")
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["CONFIG_DICT"],
                         {"HostKey": ["/etc/ssh/ssh_host_rsa_key"],
                          "AuthorizedKeysFile": [".ssh/authorized_keys"]})
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["HOSTKEYS"], ["/etc/ssh/ssh_host_rsa_key"])
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["AUTH_KEYS"],
                         {"relative": [".ssh/authorized_keys"], "absolute": []})
        self.assertTrue(parse_mock.called)
        self.assertTrue(get_path_mock.called)

    @mock.patch("moduletests.src.openssh.get_config_file_path", side_effect=["test"])
    @mock.patch("moduletests.src.openssh.parse_configuration",
                side_effect=[{"HostKey": ["/etc/ssh/ssh_host_rsa_key"],
                              "AuthorizedKeysFile": ["/var/secrets/key"]}])
    def test_ssh_problem_setup_config_vars_absolute_auth_keys(self, parse_mock, get_path_mock):
        moduletests.src.openssh.Problem.setup_config_vars()
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["CONFIG_PATH"], "test")
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["CONFIG_DICT"],
                         {"HostKey": ["/etc/ssh/ssh_host_rsa_key"],
                          "AuthorizedKeysFile": ["/var/secrets/key"]})
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["HOSTKEYS"], ["/etc/ssh/ssh_host_rsa_key"])
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["AUTH_KEYS"],
                         {"relative": [], "absolute": ["/var/secrets/key"]})
        self.assertTrue(parse_mock.called)
        self.assertTrue(get_path_mock.called)

    @mock.patch("moduletests.src.openssh.get_config_file_path", side_effect=["test"])
    @mock.patch("moduletests.src.openssh.parse_configuration", side_effect=[{}])
    def test_ssh_problem_setup_config_config_dict_empty(self, parse_mock, get_path_mock):
        moduletests.src.openssh.Problem.setup_config_vars()
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["CONFIG_PATH"], "test")
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["CONFIG_DICT"], {})
        self.assertTrue(parse_mock.called)
        self.assertTrue(get_path_mock.called)

    # noinspection PyUnresolvedReferences
    @responses.activate
    @mock.patch.dict(os.environ, {})
    @mock.patch("moduletests.src.openssh.get_config_dict", return_value={"REMEDIATE": True,
                                                                         "NOT_AN_INSTANCE": False,
                                                                         "PRIV_SEP_DIR": "/var/empty/sshd"})
    @mock.patch("moduletests.src.openssh.get_privilege_separation_dir", side_effect=[False])
    def test_ssh_problem_setup_run_vars_unset(self, get_priv_sep_dir_mock, get_config_dict_mock):
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key",
                      status=200,
                      body="test_key")
        with contextlib.redirect_stdout(StringIO()):
            moduletests.src.openssh.Problem.setup_run_vars(metadata_key_url=self.metadata_url)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["REMEDIATE"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["CREATE_NEW_KEYS"], False)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["INJECT_KEY"], False)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["INJECT_KEY_ONLY"], False)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["NEW_KEY"], "test_key")
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["PRIV_SEP_DIR"], "/var/empty/sshd")

        self.assertTrue(get_priv_sep_dir_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    # noinspection PyUnresolvedReferences
    @mock.patch.dict(os.environ, {})
    @mock.patch("moduletests.src.openssh.get_config_dict", return_value={"REMEDIATE": True,
                                                                         "NOT_AN_INSTANCE": True,
                                                                         "PRIV_SEP_DIR": "/var/empty/sshd"})
    @mock.patch("moduletests.src.openssh.get_privilege_separation_dir", side_effect=[False])
    def test_ssh_problem_setup_run_vars_unset_notaninstance(self, get_priv_sep_dir_mock, get_config_dict_mock):
        with contextlib.redirect_stdout(StringIO()):
            moduletests.src.openssh.Problem.setup_run_vars(metadata_key_url=self.metadata_url)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["NEW_KEY"], None)

        self.assertTrue(get_priv_sep_dir_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    # noinspection PyUnresolvedReferences
    @mock.patch.dict(os.environ, {"injectkey": "True",
                                  "newsshkey": "test_key"})
    @mock.patch("moduletests.src.openssh.get_config_dict", return_value={"REMEDIATE": True,
                                                                         "NOT_AN_INSTANCE": False,
                                                                         "PRIV_SEP_DIR": "/var/empty/sshd"})
    @mock.patch("moduletests.src.openssh.get_privilege_separation_dir", side_effect=[False])
    def test_ssh_problem_setup_run_vars_set_injectkey_new_key_valid(self, get_priv_sep_dir_mock, get_config_dict_mock):
        with contextlib.redirect_stdout(StringIO()):
            moduletests.src.openssh.Problem.setup_run_vars(metadata_key_url=self.metadata_url)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["REMEDIATE"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["NOT_AN_INSTANCE"], False)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["INJECT_KEY"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["NEW_KEY"], "test_key")
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["PRIV_SEP_DIR"], "/var/empty/sshd")

        self.assertTrue(get_priv_sep_dir_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    # noinspection PyUnresolvedReferences
    @mock.patch.dict(os.environ, {"injectkey": "True",
                                  "createnewkeys": "True"})
    @mock.patch("moduletests.src.openssh.get_config_dict", return_value={"REMEDIATE": True,
                                                                         "NOT_AN_INSTANCE": False,
                                                                         "PRIV_SEP_DIR": "/var/empty/sshd"})
    @mock.patch("moduletests.src.openssh.get_privilege_separation_dir", side_effect=[False])
    def test_ssh_problem_setup_run_vars_set_injectkey_create_valid(self, get_priv_sep_dir_mock, get_config_dict_mock):
        with contextlib.redirect_stdout(StringIO()):
            moduletests.src.openssh.Problem.setup_run_vars(metadata_key_url=self.metadata_url)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["REMEDIATE"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["NOT_AN_INSTANCE"], False)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["INJECT_KEY"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["CREATE_NEW_KEYS"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["NEW_KEY"], None)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["PRIV_SEP_DIR"], "/var/empty/sshd")

        self.assertTrue(get_priv_sep_dir_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    # noinspection PyUnresolvedReferences
    @mock.patch.dict(os.environ, {"injectkey": "unexpected",
                                  "newsshkey": "test_key"})
    @mock.patch("moduletests.src.openssh.get_config_dict", return_value={"REMEDIATE": True,
                                                                         "NOT_AN_INSTANCE": False,
                                                                         "PRIV_SEP_DIR": "/var/empty/sshd"})
    @mock.patch("moduletests.src.openssh.get_privilege_separation_dir", side_effect=[False])
    def test_ssh_problem_setup_run_vars_set_injectkey_invalid(self, get_priv_sep_dir_mock, get_config_dict_mock):
        with contextlib.redirect_stdout(StringIO()):
            moduletests.src.openssh.Problem.setup_run_vars(metadata_key_url=self.metadata_url)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["REMEDIATE"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["INJECT_KEY"], False)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["NEW_KEY"], "test_key")
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["PRIV_SEP_DIR"], "/var/empty/sshd")

        self.assertTrue(get_priv_sep_dir_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    # noinspection PyUnresolvedReferences
    @mock.patch.dict(os.environ, {"injectkeyonly": "True",
                                  "newsshkey": "test_key"})
    @mock.patch("moduletests.src.openssh.get_config_dict", return_value={"REMEDIATE": True,
                                                                         "NOT_AN_INSTANCE": False,
                                                                         "PRIV_SEP_DIR": "/var/empty/sshd"})
    @mock.patch("moduletests.src.openssh.get_privilege_separation_dir", side_effect=[False])
    def test_ssh_problem_setup_run_vars_set_injectkeyonly_valid(self, get_priv_sep_dir_mock, get_config_dict_mock):
        with contextlib.redirect_stdout(StringIO()):
            moduletests.src.openssh.Problem.setup_run_vars(metadata_key_url=self.metadata_url)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["REMEDIATE"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["INJECT_KEY_ONLY"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["NEW_KEY"], "test_key")
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["PRIV_SEP_DIR"], "/var/empty/sshd")

        self.assertTrue(get_priv_sep_dir_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    # noinspection PyUnresolvedReferences
    @responses.activate
    @mock.patch.dict(os.environ, {})
    @mock.patch("moduletests.src.openssh.get_config_dict", return_value={"REMEDIATE": True,
                                                                         "NOT_AN_INSTANCE": False,
                                                                         "PRIV_SEP_DIR": "/var/empty/sshd"})
    @mock.patch("moduletests.src.openssh.get_privilege_separation_dir", return_value="test_priv_sep_dir")
    def test_ssh_problem_setup_run_vars_unset_set_priv_sep_dir(self, get_priv_sep_dir_mock, get_config_dict_mock):
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key",
                      status=200,
                      body="test_key")
        with contextlib.redirect_stdout(StringIO()):
            moduletests.src.openssh.Problem.setup_run_vars(metadata_key_url=self.metadata_url)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["REMEDIATE"], True)
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["NEW_KEY"], "test_key")
        self.assertEqual(moduletests.src.openssh.Problem.CONFIG_DICT["PRIV_SEP_DIR"], "test_priv_sep_dir")

        self.assertTrue(get_priv_sep_dir_mock.called)
        self.assertTrue(get_config_dict_mock.called)

    def test_ssh_problem_instantiation(self):
        self.assertEqual(self.problem.state, "UNCHECKED")
        self.assertEqual(self.problem.item_type, "Config")
        self.assertTrue(self.problem.item is self.path)
        self.assertEqual(self.problem.value_str, "Missing")
        self.assertEqual(self.problem.info_msg, "Found bad lines in configuration file")
        self.assertTrue(self.problem.check is self.return_true)
        self.assertEqual(self.problem.check_msg, "validity of configuration")
        self.assertEqual(self.problem.fix_msg, None)
        self.assertTrue(self.problem.fix is self.return_true)

    def test_ssh_problem_property_state_invalid(self):
        self.assertEqual(self.problem.state, "UNCHECKED")
        self.problem.state = "Invalid state"
        self.assertEqual(self.problem.state, "UNCHECKED")

    def test_ssh_problem_property_item_type_invalid(self):
        self.assertEqual(self.problem.item_type, "Config")
        self.problem.item_type = "Invalid type"
        self.assertEqual(self.problem.item_type, "Config")

    def test_ssh_problem_str(self):
        self.assertEqual(str(self.problem), "UNCHECKED  Config     Missing    /tmp")

    def test_ssh_problem_get_missing_sshd_problem(self):
        problem = moduletests.src.openssh.Problem.get_missing_sshd_problem()
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_get_dupe_keyfile_lines_problem(self):
        problem = moduletests.src.openssh.Problem.get_dupe_keyfile_lines_problem()
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_get_mode_problem(self):
        this_path = moduletests.src.openssh.Path(
            path_str="/tmp", e_uid=0, e_gid=0, v_bitmask=(stat.S_IWGRP | stat.S_IWOTH))
        problem = moduletests.src.openssh.Problem.get_mode_problem(this_path)
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))
        self.assertEqual(problem.info_msg, "Permission mode includes write for groups and/or other users")

        this_path = moduletests.src.openssh.Path(
            path_str="/tmp", e_uid=0, e_gid=0, v_bitmask=(stat.S_IRWXG | stat.S_IRWXO))
        problem = moduletests.src.openssh.Problem.get_mode_problem(this_path)
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))
        self.assertEqual(problem.info_msg, "Permission mode includes permissions for groups and/or other users")

        this_path = moduletests.src.openssh.Path(path_str="/tmp", e_uid=0, e_gid=0, v_bitmask=stat.S_IWGRP)
        problem = moduletests.src.openssh.Problem.get_mode_problem(this_path)
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))
        self.assertEqual(problem.info_msg, "Permission mode includes write for groups and/or other users")

    def test_ssh_problem_get_uid_problem(self):
        this_path = moduletests.src.openssh.Path(
            path_str="/tmp", e_uid=0, e_gid=0, v_bitmask=(stat.S_IWGRP | stat.S_IWOTH))
        problem = moduletests.src.openssh.Problem.get_uid_problem(this_path)
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_get_missing_config_file_problem(self):
        problem = moduletests.src.openssh.Problem.get_missing_config_file_problem()
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_get_bad_config_options_problem(self):
        problem = moduletests.src.openssh.Problem.get_bad_config_options_problem()
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_get_missing_priv_sep_dir_problem(self):
        problem = moduletests.src.openssh.Problem.get_missing_priv_sep_dir_problem()
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_get_missing_host_keys_problem(self):
        problem = moduletests.src.openssh.Problem.get_missing_host_keys_problem()
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_get_missing_priv_sep_user_problem(self):
        problem = moduletests.src.openssh.Problem.get_missing_priv_sep_user_problem()
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_get_missing_dir_problem(self):
        problem = moduletests.src.openssh.Problem.get_missing_dir_problem(self.path)
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_get_missing_key_problem(self):
        problem = moduletests.src.openssh.Problem.get_missing_key_problem(self.path)
        self.assertTrue(isinstance(problem, moduletests.src.openssh.Problem))

    def test_ssh_problem_fix_unfixable(self):
        output = StringIO()
        with contextlib.redirect_stdout(output):
            self.assertFalse(self.problem._Problem__fix_unfixable(self.problem))
        self.assertEqual(output.getvalue(), "      Unable to automate remediation of this fault.\n")

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    def test_ssh_problem_check_missing_sshd(self, setup_config_vars_mock):
        self.problem.CONFIG_DICT["CONFIG_PATH"] = "/test"
        self.assertFalse(self.problem._Problem__check_missing_sshd())
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[OSError(errno.ENOENT, "test")])
    def test_ssh_problem_check_missing_sshd_enoent(self, setup_config_vars_mock):
        self.assertTrue(self.problem._Problem__check_missing_sshd())
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[OSError(errno.EEXIST, "test")])
    def test_ssh_problem_check_missing_sshd_eexist(self, setup_config_vars_mock):
        self.assertFalse(self.problem._Problem__check_missing_sshd())
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[subprocess.CalledProcessError(
        returncode=0, cmd="test")])
    def test_ssh_problem_check_missing_sshd_cpe(self, setup_config_vars_mock):
        self.assertFalse(self.problem._Problem__check_missing_sshd())
        self.assertTrue(setup_config_vars_mock.called)

    def test_ssh_problem_check_dupe_keyfile_lines_found(self):
        self.problem.CONFIG_DICT["CONFIG_PATH"] = "/test"
        open_mock = mock.mock_open(read_data="AuthorizedKeysFile a\nAuthorizedKeysFile a\n")
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("moduletests.src.openssh.open", open_mock):
            self.assertTrue(self.problem._Problem__check_dupe_keyfile_lines())

    def test_ssh_problem_check_dupe_keyfile_lines_not_found(self):
        self.problem.CONFIG_DICT["CONFIG_PATH"] = "/test"
        open_mock = mock.mock_open(read_data="Port 22\n# test\nAuthorizedKeysFile\n\n")
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("moduletests.src.openssh.open", open_mock):
            self.assertFalse(self.problem._Problem__check_dupe_keyfile_lines())

    @mock.patch("subprocess.check_output", side_effect=[True])
    def test_ssh_problem_check_bad_config_options_not_found(self, check_output_mock):
        self.assertFalse(self.problem._Problem__check_bad_config_options())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        1, "test",
        "super awesome message\n"
        "/etc/ssh/sshd_config: terminating, 2 bad configuration options\n"))
    def test_ssh_problem_check_bad_config_options_exception(self, check_output_mock):
        with self.assertRaises(Exception) as ex:
            self.problem._Problem__check_bad_config_options()
            self.assertEqual(ex.args, ("super awesome message\n",))
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        1, "test",
        "/etc/ssh/sshd_config: line 1: Bad configuration option: badoption\n"
        "/etc/ssh/sshd_config line 2: missing integer value.\n"
        "/etc/ssh/sshd_config: terminating, 2 bad configuration options\n"))
    def test_ssh_problem_check_bad_config_options_found(self, check_output_mock):
        self.assertTrue(self.problem._Problem__check_bad_config_options())
        self.assertEqual(self.problem.value, [1, 2])
        self.assertEqual(self.problem.value_str, "1,2")
        self.assertEqual(self.problem.fix_msg, "Remove/fix lines:     1,2 in /etc/ssh/sshd_config")
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1, "test", "debug2: load_server_config: filename test_path"))
    def test_ssh_problem_check_bad_config_options_cpe_not_found(self, check_output_mock):
        self.assertFalse(self.problem._Problem__check_bad_config_options())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        1, "test", "Missing privilege separation directory: /var/empty"))
    def test_ssh_problem_check_missing_priv_sep_dir_found(self, check_output_mock):
        self.assertTrue(self.problem._Problem__check_missing_priv_sep_dir())
        self.assertTrue(isinstance(self.problem.item, moduletests.src.openssh.Path))
        self.assertEqual(self.problem.fix_msg, "Create privilege separation directory: /var/empty")
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        1, "test", "Some error"))
    def test_ssh_problem_check_missing_priv_sep_dir_cpe_not_found(self, check_output_mock):
        self.assertFalse(self.problem._Problem__check_missing_priv_sep_dir())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=[True])
    def test_ssh_problem_check_missing_priv_sep_dir_not_found(self, check_output_mock):
        self.assertFalse(self.problem._Problem__check_missing_priv_sep_dir())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        1, "test", "sshd: no hostkeys available -- exiting."))
    def test_ssh_problem_check_missing_host_keys_not_found(self, check_output_mock):
        self.assertTrue(self.problem._Problem__check_missing_host_keys())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        1, "test", "Some other error"))
    def test_ssh_problem_check_missing_host_keys_cpe_not_found(self, check_output_mock):
        self.assertFalse(self.problem._Problem__check_missing_host_keys())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=[True])
    def test_ssh_problem_check_missing_host_keys_found(self, check_output_mock):
        self.assertFalse(self.problem._Problem__check_missing_host_keys())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=[True])
    def test_ssh_problem_check_missing_priv_sep_user_not_found(self, check_output_mock):
        self.assertFalse(self.problem._Problem__check_missing_priv_sep_user())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        1, "test", "Privilege separation user sshd does not exist"))
    def test_ssh_problem_check_missing_priv_sep_user_found(self, check_output_mock):
        self.assertTrue(self.problem._Problem__check_missing_priv_sep_user())
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        1, "test", "Some other error"))
    def test_ssh_problem_check_missing_priv_sep_user_cpe_not_found(self, check_output_mock):
        self.assertFalse(self.problem._Problem__check_missing_priv_sep_user())
        self.assertTrue(check_output_mock.called)

    @mock.patch("os.path.isdir", side_effect=[True, False])
    @mock.patch("os.stat")
    def test_ssh_problem_check_mode(self, stat_mock, isdir_mock):
        stat_mock.return_value = mock.Mock(st_mode=0o777)
        # Mode based on file being a directory
        self.assertTrue(self.problem._Problem__check_mode())
        self.assertEqual(self.problem.item.e_mode, 0o755)
        # Mode based on file being a file
        self.assertTrue(self.problem._Problem__check_mode())
        self.assertEqual(self.problem.item.e_mode, 0o655)
        # No problem found
        self.problem.item.v_bitmask = 0b0
        self.assertFalse(self.problem._Problem__check_mode())
        self.assertTrue(stat_mock.called)
        self.assertTrue(isdir_mock.called)

    @mock.patch("os.stat")
    def test_ssh_problem_check_uid(self, os_mock):
        os_mock.return_value = mock.Mock(st_uid=666)
        self.assertTrue(self.problem._Problem__check_uid())
        self.problem.item.e_uid = 666
        self.assertFalse(self.problem._Problem__check_uid())
        self.assertTrue(os_mock.called)

    @mock.patch("os.path.isdir", side_effect=[True, False])
    def test_ssh_check_missing_dir(self, os_mock):
        self.assertFalse(self.problem._Problem__check_missing_dir())
        self.assertTrue(self.problem._Problem__check_missing_dir())
        self.assertTrue(os_mock.called)

    @mock.patch("os.path.isfile", side_effect=[True, False])
    def test_ssh_check_missing_file(self, os_mock):
        self.assertFalse(self.problem._Problem__check_missing_file())
        self.assertTrue(self.problem._Problem__check_missing_file())
        self.assertTrue(os_mock.called)

    @mock.patch("subprocess.check_output", side_effect=[True])
    def test_ssh_check_missing_config_file(self, subprocess_mock):
        self.assertFalse(self.problem._Problem__check_missing_config_file())
        self.assertTrue(subprocess_mock.called)

    @mock.patch("subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1, "test",
                                                          "/etc/ssh/sshd_config: No such file or directory"))
    def test_ssh_check_missing_config_file_cpe_no_such(self, subprocess_mock):
        self.assertTrue(self.problem._Problem__check_missing_config_file())
        self.assertTrue(subprocess_mock.called)

    @mock.patch("subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1, "test",
                                                          "Not the problem we are looking for"))
    def test_ssh_check_missing_config_file_cpe_other(self, subprocess_mock):
        self.assertFalse(self.problem._Problem__check_missing_config_file())
        self.assertTrue(subprocess_mock.called)

    def test_ssh_problem_fix_mode_incorrect_item_type(self):
        with self.assertRaises(Exception) as ex:
            self.problem.item_type = "Incorrect"
            self.problem._Problem__fix_mode()
            self.assertEqual(ex, "Incorrect remediation function for this_problem type: Incorrect")

    @mock.patch("os.stat")
    @mock.patch("os.chmod", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_mode", side_effect=[False])
    def test_ssh_problem_fix_mode_fixed(self, check_mode_mock, os_chmod_mock, os_stat_mock):
        os_stat_mock.return_value = mock.Mock(st_mode=0o777)
        self.problem.item_type = "Mode"
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(self.problem._Problem__fix_mode())
            self.assertTrue(check_mode_mock.called)
            self.assertTrue(os_chmod_mock.called)
            self.assertTrue(os_stat_mock.called)

    @mock.patch("os.stat")
    @mock.patch("os.chmod", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_mode", side_effect=[True])
    def test_ssh_problem_fix_mode_not_fixed(self, check_mode_mock, os_chmod_mock, os_stat_mock):
        os_stat_mock.return_value = mock.Mock(st_mode=0o777)
        self.problem.item_type = "Mode"
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_mode())
            self.assertTrue(check_mode_mock.called)
            self.assertTrue(os_chmod_mock.called)
            self.assertTrue(os_stat_mock.called)

    def test_ssh_problem_fix_uid_incorrect_item_type(self):
        with self.assertRaises(Exception) as ex:
            self.problem.item_type = "Incorrect"
            self.problem._Problem__fix_uid()
            self.assertEqual(ex, "Incorrect remediation function for this_problem type: Incorrect")

    @mock.patch("os.stat")
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_uid", side_effect=[False])
    def test_ssh_problem_fix_uid_fixed(self, check_uid_mock, os_chown_mock, os_stat_mock):
        os_stat_mock.return_value = mock.Mock(st_uid=1)
        self.problem.item_type = "UID"
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(self.problem._Problem__fix_uid())
            self.assertTrue(check_uid_mock.called)
            self.assertTrue(os_chown_mock.called)
            self.assertTrue(os_stat_mock.called)

    @mock.patch("os.stat")
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_uid", side_effect=[True])
    def test_ssh_problem_fix_uid_not_fixed(self, check_uid_mock, os_chown_mock, os_stat_mock):
        os_stat_mock.return_value = mock.Mock(st_uid=1)
        self.problem.item_type = "UID"
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_uid())
            self.assertTrue(check_uid_mock.called)
            self.assertTrue(os_chown_mock.called)
            self.assertTrue(os_stat_mock.called)

    @mock.patch("moduletests.src.openssh.backup", side_effect=[True])
    @mock.patch("shutil.copystat", side_effect=[True])
    @mock.patch("shutil.copy2", side_effect=[True])
    @mock.patch("os.stat")
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_dupe_keyfile_lines", side_effect=[False])
    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    def test_ssh_problem_fix_dup_keyfile_lines_fixed(self,
                                                     setup_config_vars_mock,
                                                     check_dup_keyfile_lines_mock,
                                                     os_chown_mock,
                                                     os_stat_mock,
                                                     copy2_mock,
                                                     copystat_mock,
                                                     backup_mock):
        open_mock = mock.mock_open(read_data="AuthorizedKeysFile a\nAuthorizedKeysFile b\nPort 22\n")
        os_stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0)
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")

        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func

        self.problem.value = dict()
        self.problem.value["line_nums"] = [1, 2]
        # A set is used in the actual function, but since sets are not ordered, instead, use a list so there is
        # only one possible valid outcome
        self.problem.value["values"] = ["a", "b"]
        # noinspection PyUnresolvedReferences
        with mock.patch.object(moduletests.src.openssh.tempfile, "NamedTemporaryFile") as temp_file_mock:
            with mock.patch("moduletests.src.openssh.open", open_mock):
                with contextlib.redirect_stdout(StringIO()):
                    self.assertTrue(self.problem._Problem__fix_dup_keyfile_lines())
                    self.assertTrue(temp_file_mock.called)
                    self.assertEqual(str(temp_file_mock.mock_calls),
                                     "[call(mode='wt'),\n call().__enter__(),\n "
                                     "call().__enter__().write('# AuthorizedKeysFile a # commented out by "
                                     "ec2rl\\n'),\n "
                                     "call().__enter__().write('# AuthorizedKeysFile b # commented out by "
                                     "ec2rl\\n'),\n "
                                     "call().__enter__().write('AuthorizedKeysFile a b\\n'),\n "
                                     "call().__enter__().write('Port 22\\n'),\n "
                                     "call().__enter__().flush(),\n "
                                     "call().__exit__(None, None, None)]")
                    self.assertTrue(open_mock.called)
                    self.assertTrue(backup_mock.called)
                    self.assertTrue(copystat_mock.called)
                    self.assertTrue(copy2_mock.called)
                    self.assertTrue(setup_config_vars_mock.called)
                    self.assertTrue(check_dup_keyfile_lines_mock.called)
                    self.assertTrue(os_chown_mock.called)
                    self.assertTrue(os_stat_mock.called)

    @mock.patch("moduletests.src.openssh.backup", side_effect=[True])
    @mock.patch("shutil.copystat", side_effect=[True])
    @mock.patch("shutil.copy2", side_effect=[True])
    @mock.patch("os.stat")
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_dupe_keyfile_lines", side_effect=[True])
    @mock.patch("moduletests.src.openssh.restore", side_effect=[True])
    def test_ssh_problem_fix_dup_keyfile_lines_not_fixed(self,
                                                         restore_mock,
                                                         check_dup_keyfile_lines_mock,
                                                         os_chown_mock,
                                                         os_stat_mock,
                                                         copy2_mock,
                                                         copystat_mock,
                                                         backup_mock):
        open_mock = mock.mock_open(read_data="AuthorizedKeysFile a\nAuthorizedKeysFile b\nPort 22\n")
        os_stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0)
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")

        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func

        self.problem.value = dict()
        self.problem.value["line_nums"] = [1, 2]
        # A set is used in the actual function, but since sets are not ordered, instead, use a list so there is
        # only one possible valid outcome
        self.problem.value["values"] = ["a", "b"]
        # noinspection PyUnresolvedReferences
        with mock.patch.object(moduletests.src.openssh.tempfile, "NamedTemporaryFile") as temp_file_mock:
            with mock.patch("moduletests.src.openssh.open", open_mock):
                with contextlib.redirect_stdout(StringIO()):
                    self.assertFalse(self.problem._Problem__fix_dup_keyfile_lines())
                    self.assertTrue(temp_file_mock.called)
                    self.assertEqual(str(temp_file_mock.mock_calls),
                                     "[call(mode='wt'),\n call().__enter__(),\n "
                                     "call().__enter__().write('# AuthorizedKeysFile a # commented out by "
                                     "ec2rl\\n'),\n "
                                     "call().__enter__().write('# AuthorizedKeysFile b # commented out by "
                                     "ec2rl\\n'),\n "
                                     "call().__enter__().write('AuthorizedKeysFile a b\\n'),\n "
                                     "call().__enter__().write('Port 22\\n'),\n "
                                     "call().__enter__().flush(),\n "
                                     "call().__exit__(None, None, None)]")
                    self.assertTrue(open_mock.called)
                    self.assertTrue(backup_mock.called)
                    self.assertTrue(copystat_mock.called)
                    self.assertTrue(copy2_mock.called)
                    self.assertTrue(restore_mock.called)
                    self.assertTrue(check_dup_keyfile_lines_mock.called)
                    self.assertTrue(os_chown_mock.called)
                    self.assertTrue(os_stat_mock.called)

    @mock.patch("moduletests.src.openssh.open", new_callable=mock.mock_open())
    @mock.patch("os.chmod", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_config_file", side_effect=[False])
    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    def test_ssh_problem_fix_write_default_config_fixed(self,
                                                        setup_config_vars_mock,
                                                        check_missing_config_file_mock,
                                                        os_chmod_mock,
                                                        open_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(self.problem._Problem__fix_write_default_config())
        self.assertTrue("call().__enter__().writelines(["
                        "'HostKey /etc/ssh/ssh_host_rsa_key\\n', "
                        "'HostKey /etc/ssh/ssh_host_ecdsa_key\\n', "
                        "'HostKey /etc/ssh/ssh_host_ed25519_key\\n', "
                        "'SyslogFacility AUTHPRIV\\n', "
                        "'PermitRootLogin no\\n', "
                        "'AuthorizedKeysFile .ssh/authorized_keys\\n', "
                        "'PasswordAuthentication no\\n', "
                        "'ChallengeResponseAuthentication no\\n', "
                        "'UsePAM yes\\n']),\n " in str(open_mock.mock_calls))
        self.assertTrue(setup_config_vars_mock.called)
        self.assertTrue(check_missing_config_file_mock.called)
        self.assertTrue(os_chmod_mock.called)

    @mock.patch("moduletests.src.openssh.open", new_callable=mock.mock_open())
    @mock.patch("os.chmod", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_config_file", side_effect=[True])
    def test_ssh_problem_fix_write_default_config_not_fixed(self,
                                                            check_missing_config_file_mock,
                                                            os_chmod_mock,
                                                            open_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_write_default_config())
        self.assertTrue("call().__enter__().writelines(["
                        "'HostKey /etc/ssh/ssh_host_rsa_key\\n', "
                        "'HostKey /etc/ssh/ssh_host_ecdsa_key\\n', "
                        "'HostKey /etc/ssh/ssh_host_ed25519_key\\n', "
                        "'SyslogFacility AUTHPRIV\\n', "
                        "'PermitRootLogin no\\n', "
                        "'AuthorizedKeysFile .ssh/authorized_keys\\n', "
                        "'PasswordAuthentication no\\n', "
                        "'ChallengeResponseAuthentication no\\n', "
                        "'UsePAM yes\\n']),\n " in str(open_mock.mock_calls))
        self.assertTrue(check_missing_config_file_mock.called)
        self.assertTrue(os_chmod_mock.called)

    @mock.patch("moduletests.src.openssh.open", side_effect=OSError())
    def test_ssh_problem_fix_write_default_config_error(self, open_mock):
        self.assertFalse(self.problem._Problem__fix_write_default_config())
        self.assertTrue(open_mock.called)

    @mock.patch("moduletests.src.openssh.backup", side_effect=[True])
    @mock.patch("shutil.copystat", side_effect=[True])
    @mock.patch("shutil.copy2", side_effect=[True])
    @mock.patch("os.stat")
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_bad_config_options", side_effect=[False])
    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    def test_ssh_problem_fix_comment_bad_config_lines_fixed(self,
                                                            setup_config_vars_mock,
                                                            check_back_config_options_mock,
                                                            os_chown_mock,
                                                            os_stat_mock,
                                                            copy2_mock,
                                                            copystat_mock,
                                                            backup_mock):
        open_mock = mock.mock_open(read_data="BadOptionOne a\nGoodOptionOne b\nBadOptionTwo c\n")
        os_stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0)
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")

        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func

        self.problem.value = [1, 3]
        # noinspection PyUnresolvedReferences
        with mock.patch.object(moduletests.src.openssh.tempfile, "NamedTemporaryFile") as temp_file_mock:
            with mock.patch("moduletests.src.openssh.open", open_mock):
                with contextlib.redirect_stdout(StringIO()):
                    self.assertTrue(self.problem._Problem__fix_comment_bad_config_lines())
                    self.assertTrue(temp_file_mock.called)
                    self.assertEqual(str(temp_file_mock.mock_calls),
                                     "[call(mode='wt'),\n call().__enter__(),\n "
                                     "call().__enter__().write('# BadOptionOne a # commented out by ec2rl\\n'),\n "
                                     "call().__enter__().write('GoodOptionOne b\\n'),\n "
                                     "call().__enter__().write('# BadOptionTwo c # commented out by ec2rl\\n'),\n "
                                     "call().__enter__().flush(),\n "
                                     "call().__exit__(None, None, None)]")
                    self.assertTrue(open_mock.called)
                    self.assertTrue(setup_config_vars_mock.called)
                    self.assertTrue(check_back_config_options_mock.called)
                    self.assertTrue(os_chown_mock.called)
                    self.assertTrue(os_stat_mock.called)
                    self.assertTrue(copy2_mock.called)
                    self.assertTrue(copystat_mock.called)
                    self.assertTrue(backup_mock.called)

    @mock.patch("moduletests.src.openssh.backup", side_effect=[True])
    @mock.patch("shutil.copystat", side_effect=[True])
    @mock.patch("shutil.copy2", side_effect=[True])
    @mock.patch("os.stat")
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_bad_config_options", side_effect=[True])
    @mock.patch("moduletests.src.openssh.restore", side_effect=[True])
    def test_ssh_problem_fix_comment_bad_config_lines_not_fixed(self,
                                                                restore_mock,
                                                                check_back_config_options_mock,
                                                                os_chown_mock,
                                                                os_stat_mock,
                                                                copy2_mock,
                                                                copystat_mock,
                                                                backup_mock):
        open_mock = mock.mock_open(read_data="BadOptionOne a\nGoodOptionOne b\nBadOptionTwo c\n")
        os_stat_mock.return_value = mock.Mock(st_uid=0, st_gid=0)
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")

        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func

        self.problem.value = [1, 3]
        # noinspection PyUnresolvedReferences
        with mock.patch.object(moduletests.src.openssh.tempfile, "NamedTemporaryFile") as temp_file_mock:
            with mock.patch("moduletests.src.openssh.open", open_mock):
                with contextlib.redirect_stdout(StringIO()):
                    self.assertFalse(self.problem._Problem__fix_comment_bad_config_lines())
                    self.assertTrue(temp_file_mock.called)
                    self.assertEqual(str(temp_file_mock.mock_calls),
                                     "[call(mode='wt'),\n call().__enter__(),\n "
                                     "call().__enter__().write('# BadOptionOne a # commented out by ec2rl\\n'),\n "
                                     "call().__enter__().write('GoodOptionOne b\\n'),\n "
                                     "call().__enter__().write('# BadOptionTwo c # commented out by ec2rl\\n'),\n "
                                     "call().__enter__().flush(),\n "
                                     "call().__exit__(None, None, None)]")
                    self.assertTrue(open_mock.called)
                    self.assertTrue(restore_mock.called)
                    self.assertTrue(check_back_config_options_mock.called)
                    self.assertTrue(os_chown_mock.called)
                    self.assertTrue(os_stat_mock.called)
                    self.assertTrue(copy2_mock.called)
                    self.assertTrue(copystat_mock.called)
                    self.assertTrue(backup_mock.called)

    @mock.patch("os.makedirs", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_priv_sep_dir", side_effect=[False])
    def test_ssh_problem_fix_missing_priv_sep_dir_fixed(self, check_mock, os_makedirs_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(self.problem._Problem__fix_missing_priv_sep_dir())
            self.assertTrue(check_mock.called)
            self.assertTrue(os_makedirs_mock.called)

    @mock.patch("os.makedirs", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_priv_sep_dir", side_effect=[True])
    def test_ssh_problem_fix_missing_priv_sep_dir_not_fixed(self, check_mock, os_makedirs_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_missing_priv_sep_dir())
            self.assertTrue(check_mock.called)
            self.assertTrue(os_makedirs_mock.called)

    @mock.patch("os.makedirs", side_effect=OSError)
    def test_ssh_problem_fix_missing_priv_sep_dir_exception(self, os_makedirs_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_missing_priv_sep_dir())
            self.assertTrue(os_makedirs_mock.called)

    @mock.patch("os.path.exists", side_effect=[True] * 3 + [False])
    @mock.patch("moduletests.src.openssh.backup", side_effect=["/tmp"] * 3)
    @mock.patch("os.path.isfile", side_effect=[True] * 2 + [False] * 1)
    @mock.patch("os.remove", side_effect=[True] * 2)
    @mock.patch("shutil.rmtree", side_effect=[True])
    @mock.patch("subprocess.check_call")
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_host_keys", side_effect=[False])
    def test_ssh_problem_fix_create_hostkeys_fixed(self,
                                                   check_mock,
                                                   check_call_mock,
                                                   shutil_rmtree_mock,
                                                   os_remove_mock,
                                                   os_path_isfile_mock,
                                                   backup_mock,
                                                   os_path_exists_mock):
        check_call_mock.return_value = 0
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(self.problem._Problem__fix_create_hostkeys())
            self.assertTrue(check_call_mock.called)
            self.assertTrue(shutil_rmtree_mock.called)
            self.assertTrue(os_remove_mock.called)
            self.assertTrue(os_path_isfile_mock.called)
            self.assertTrue(backup_mock.called)
            self.assertTrue(os_path_exists_mock.called)
            self.assertTrue(check_mock.called)

    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_host_keys", side_effect=[True])
    @mock.patch("os.path.exists", side_effect=[True] * 3 + [False])
    @mock.patch("moduletests.src.openssh.backup", side_effect=["/tmp"] * 3)
    @mock.patch("os.path.isfile", side_effect=[True] * 2 + [False] * 1)
    @mock.patch("os.remove", side_effect=[True] * 2)
    @mock.patch("shutil.rmtree", side_effect=[True])
    @mock.patch("subprocess.check_call")
    def test_ssh_problem_fix_create_hostkeys_not_fixed(self,
                                                       check_call_mock,
                                                       shutil_rmtree_mock,
                                                       os_remove_mock,
                                                       os_path_isfile_mock,
                                                       backup_mock,
                                                       os_path_exists_mock,
                                                       check_mock):
        check_call_mock.return_value = 0
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_create_hostkeys())
            self.assertTrue(check_call_mock.called)
            self.assertTrue(shutil_rmtree_mock.called)
            self.assertTrue(os_remove_mock.called)
            self.assertTrue(os_path_isfile_mock.called)
            self.assertTrue(backup_mock.called)
            self.assertTrue(os_path_exists_mock.called)
            self.assertTrue(check_mock.called)

    @mock.patch("os.path.exists", side_effect=[True])
    @mock.patch("moduletests.src.openssh.backup", side_effect=["/tmp"])
    @mock.patch("os.path.isfile", side_effect=[True])
    @mock.patch("os.remove", side_effect=[True])
    @mock.patch("subprocess.check_call", side_effect=subprocess.CalledProcessError(1, "ssh-keygen"))
    def test_ssh_problem_fix_create_hostkeys_exception(self,
                                                       check_call_mock,
                                                       os_remove_mock,
                                                       os_path_isfile_mock,
                                                       backup_mock,
                                                       os_path_exists_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_create_hostkeys())
            self.assertTrue(check_call_mock.called)
            self.assertTrue(os_remove_mock.called)
            self.assertTrue(os_path_isfile_mock.called)
            self.assertTrue(backup_mock.called)
            self.assertTrue(os_path_exists_mock.called)

    @mock.patch("moduletests.src.openssh.open", new_callable=mock.mock_open())
    @mock.patch("subprocess.check_call")
    @mock.patch("os.chmod", side_effect=[True])
    @mock.patch("os.stat")
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_priv_sep_user", side_effect=[False])
    def test_ssh_problem_fix_missing_priv_sep_user_fixed(self,
                                                         check_mock,
                                                         os_chmod_mock,
                                                         os_stat_mock,
                                                         check_call_mock,
                                                         open_mock):
        os_stat_mock.return_value = mock.Mock(st_mode=0o600)
        check_call_mock.return_value = 0
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(self.problem._Problem__fix_missing_priv_sep_user())
            self.assertTrue(check_mock.called)
            self.assertTrue(open_mock.called)
            self.assertTrue(check_call_mock.called)
            self.assertTrue(os_chmod_mock.called)
            self.assertTrue(os_stat_mock.called)

    @mock.patch("moduletests.src.openssh.open", new_callable=mock.mock_open())
    @mock.patch("subprocess.check_call")
    @mock.patch("os.chmod", side_effect=[True])
    @mock.patch("os.stat")
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_priv_sep_user", side_effect=[True])
    def test_ssh_problem_fix_missing_priv_sep_user_not_fixed(self,
                                                             check_mock,
                                                             os_chmod_mock,
                                                             os_stat_mock,
                                                             check_call_mock,
                                                             open_mock):
        os_stat_mock.return_value = mock.Mock(st_mode=0o600)
        check_call_mock.return_value = 0
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_missing_priv_sep_user())
            self.assertTrue(check_mock.called)
            self.assertTrue(open_mock.called)
            self.assertTrue(check_call_mock.called)
            self.assertTrue(os_chmod_mock.called)
            self.assertTrue(os_stat_mock.called)

    @mock.patch("moduletests.src.openssh.open", side_effect=OSError())
    def test_ssh_problem_fix_missing_priv_sep_user_exception(self, open_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_missing_priv_sep_user())
            self.assertTrue(open_mock.called)

    @mock.patch("os.makedirs", side_effect=[True])
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_dir", side_effect=[False])
    def test_ssh_problem_fix_missing_dir_fixed(self, check_mock, os_chown_mock, os_makedirs_mock):
        self.assertTrue(self.problem._Problem__fix_missing_dir())
        self.assertTrue(check_mock.called)
        self.assertTrue(os_chown_mock.called)
        self.assertTrue(os_makedirs_mock.called)

    @mock.patch("os.makedirs", side_effect=OSError())
    def test_ssh_problem_fix_missing_dir_exception(self, os_makedirs_mock):
        self.assertFalse(self.problem._Problem__fix_missing_dir())
        self.assertTrue(os_makedirs_mock.called)

    @mock.patch("os.makedirs", side_effect=[True])
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_dir", side_effect=[True])
    def test_ssh_problem_fix_missing_dir_not_fixed(self, check_mock, os_chown_mock, os_makedirs_mock):
        self.assertFalse(self.problem._Problem__fix_missing_dir())
        self.assertTrue(check_mock.called)
        self.assertTrue(os_chown_mock.called)
        self.assertTrue(os_makedirs_mock.called)

    @mock.patch("os.mknod", side_effect=[True])
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.inject_key_single", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_file", side_effect=[False])
    def test_ssh_problem_fix_missing_key_file_fixed(self, check_mock, inject_mock, os_chown_mock, os_mknod_mock):
        self.problem.item.e_mode = 0o600
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(self.problem._Problem__fix_missing_key_file())
        self.assertTrue(check_mock.called)
        self.assertTrue(inject_mock.called)
        self.assertTrue(os_chown_mock.called)
        self.assertTrue(os_mknod_mock.called)

    @mock.patch("os.mknod", side_effect=[True])
    @mock.patch("os.chown", side_effect=[True])
    @mock.patch("moduletests.src.openssh.inject_key_single", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem._Problem__check_missing_file", side_effect=[True])
    def test_ssh_problem_fix_missing_key_file_not_fixed(self, check_mock, inject_mock, os_chown_mock, os_mknod_mock):
        self.problem.item.e_mode = 0o600
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_missing_key_file())
            self.assertTrue(check_mock.called)
            self.assertTrue(inject_mock.called)
            self.assertTrue(os_chown_mock.called)
            self.assertTrue(os_mknod_mock.called)

    @mock.patch("os.mknod", side_effect=OSError())
    def test_ssh_problem_fix_missing_key_file_exception(self, os_mknod_mock):
        self.problem.item.e_mode = 0o600
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(self.problem._Problem__fix_missing_key_file())
            self.assertTrue(os_mknod_mock.called)

    @mock.patch("moduletests.src.openssh.subprocess.check_call", side_effect=[True])
    @mock.patch("moduletests.src.openssh.open")
    @mock.patch("moduletests.src.openssh.os.remove", side_effect=[True, True])
    def test_ssh_generate_rsa_key_pair_success(self, os_remove_mock, open_mock, subprocess_mock):
        key_path = "test_path"

        pub_open_mock = mock.mock_open(read_data="pub_key_value")
        priv_open_mock = mock.mock_open(read_data="priv_key_value")
        open_mock.side_effect = [pub_open_mock.return_value, priv_open_mock.return_value]
        self.assertEqual(moduletests.src.openssh.generate_rsa_key_pair(key_path), {"public": "pub_key_value",
                                                                                   "private": "priv_key_value"})

        self.assertEqual(os_remove_mock.call_count, 2)
        self.assertTrue(os_remove_mock.called)
        self.assertTrue(open_mock.called)
        self.assertTrue(subprocess_mock.called)

    @mock.patch("moduletests.src.openssh.subprocess.check_call", side_effect=subprocess.CalledProcessError(2, "cmd"))
    @mock.patch("moduletests.src.openssh.os.remove", side_effect=[IOError, IOError])
    def test_ssh_generate_rsa_key_pair_remove_error(self, os_remove_mock, subprocess_mock):
        key_path = "test_path"

        with self.assertRaises(subprocess.CalledProcessError):
            moduletests.src.openssh.generate_rsa_key_pair(key_path)

        self.assertEqual(os_remove_mock.call_count, 2)
        self.assertTrue(os_remove_mock.called)
        self.assertTrue(subprocess_mock.called)

    def test_ssh_key_injection_driver_failure(self):
        sys_config_dict = {"NEW_KEY": None,
                           "CREATE_NEW_KEYS": False}
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(moduletests.src.openssh.key_injection_driver(sys_config_dict))

    @mock.patch("moduletests.src.openssh.inject_key_all", side_effect=OSError)
    def test_ssh_key_injection_driver_exception(self, inject_key_mock):
        sys_config_dict = {"NEW_KEY": "test_key",
                           "AUTH_KEYS": "",
                           "BACKED_FILES": "",
                           "BACKUP_DIR": ""}
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(moduletests.src.openssh.key_injection_driver(sys_config_dict))

        self.assertTrue(inject_key_mock.called)

    @mock.patch("moduletests.src.openssh.inject_key_all", side_effect=[True])
    def test_ssh_key_injection_driver_new_key_success(self, inject_key_mock):
        sys_config_dict = {"NEW_KEY": "test_key",
                           "AUTH_KEYS": "",
                           "BACKED_FILES": "",
                           "BACKUP_DIR": ""}
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(moduletests.src.openssh.key_injection_driver(sys_config_dict))

        self.assertTrue(inject_key_mock.called)

    @mock.patch("moduletests.src.openssh.os.path.exists", return_value=True)
    @mock.patch("moduletests.src.openssh.generate_rsa_key_pair", return_value={"public": "pub_key",
                                                                               "private": "priv_key"})
    @mock.patch("moduletests.src.openssh.get_instance_id", return_value="i-test_id")
    @mock.patch("moduletests.src.openssh.get_instance_region", return_value="us-east-1")
    @mock.patch("moduletests.src.openssh.boto3.client")
    @mock.patch("moduletests.src.openssh.inject_key_all", side_effect=[True])
    def test_ssh_key_injection_driver_create_key_success(self,
                                                         inject_key_mock,
                                                         client_mock,
                                                         get_instance_region_mock,
                                                         get_instance_id_mock,
                                                         gen_key_pair_mock,
                                                         exists_mock):
        sys_config_dict = {"NEW_KEY": None,
                           "CREATE_NEW_KEYS": True,
                           "AUTH_KEYS": "",
                           "BACKED_FILES": "",
                           "BACKUP_DIR": ""}
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(moduletests.src.openssh.key_injection_driver(sys_config_dict))

        self.assertEqual(str(client_mock.mock_calls),
                         "[call('ssm', region_name='us-east-1'),\n "
                         "call().put_parameter("
                         "Description='Private key added to instance i-test_id by EC2 Rescue for Linux.', "
                         "Name='/ec2rl/openssh/i-test_id/key', "
                         "Overwrite=True, "
                         "Type='SecureString', "
                         "Value='priv_key')]")

        self.assertTrue(inject_key_mock.called)
        self.assertTrue(client_mock.called)
        self.assertTrue(get_instance_region_mock.called)
        self.assertTrue(get_instance_id_mock.called)
        self.assertTrue(gen_key_pair_mock.called)
        self.assertTrue(exists_mock.called)

    @mock.patch("moduletests.src.openssh.os.path.exists", return_value=False)
    @mock.patch("moduletests.src.openssh.os.makedirs", side_effect=[True])
    @mock.patch("moduletests.src.openssh.generate_rsa_key_pair", return_value={"public": "pub_key",
                                                                               "private": "priv_key"})
    @mock.patch("moduletests.src.openssh.get_instance_id", return_value="i-test_id")
    @mock.patch("moduletests.src.openssh.get_instance_region", return_value="us-east-1")
    @mock.patch("moduletests.src.openssh.boto3.client", side_effect=botocore.exceptions.NoCredentialsError())
    def test_ssh_key_injection_driver_create_key_missing_creds(self,
                                                               client_mock,
                                                               get_instance_region_mock,
                                                               get_instance_id_mock,
                                                               gen_key_pair_mock,
                                                               makedirs_mock,
                                                               exists_mock):
        sys_config_dict = {"NEW_KEY": None,
                           "CREATE_NEW_KEYS": True,
                           "AUTH_KEYS": "",
                           "BACKED_FILES": "",
                           "BACKUP_DIR": ""}
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(moduletests.src.openssh.key_injection_driver(sys_config_dict))

        self.assertTrue(client_mock.called)
        self.assertTrue(get_instance_region_mock.called)
        self.assertTrue(get_instance_id_mock.called)
        self.assertTrue(gen_key_pair_mock.called)
        self.assertTrue(makedirs_mock.called)
        self.assertTrue(exists_mock.called)

    @mock.patch("moduletests.src.openssh.inject_key_single", side_effect=[True, True])
    @mock.patch("os.path.basename", side_effect=["test", "test"])
    @mock.patch("moduletests.src.openssh.backup", side_effect=["/test_backup_dir/file1",
                                                               "/test_backup_dir/file2"])
    @mock.patch("os.path.isfile", side_effect=[False, True, True])
    @mock.patch("pwd.getpwnam")
    @mock.patch("os.path.isdir", side_effect=[True])
    @mock.patch("os.path.realpath", side_effect=["/one/two/three/file1", "/var/secrets/file2", "/home/testuser"])
    @mock.patch("glob.glob")
    def test_ssh_inject_key_all(self,
                                glob_mock,
                                os_path_realpath_mock,
                                os_path_isdir_mock,
                                pwd_getpwnam_mock,
                                os_path_isfile_mock,
                                backup_mock,
                                os_path_basename_mock,
                                inject_key_single_mock):
        glob_mock.return_value = ["/home/testuser"]
        pwd_getpwnam_mock.return_value.pw_uid = 1337
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(moduletests.src.openssh.inject_key_all("new_key",
                                                                   {"absolute": ["/one/two/three/file1",
                                                                                 "/var/secrets/file2"],
                                                                    "relative": ["auth_keys"]},
                                                                   {},
                                                                   "backup_dir"))
        self.assertTrue(glob_mock.called)
        self.assertTrue(os_path_realpath_mock.called)
        self.assertTrue(os_path_isdir_mock.called)
        self.assertTrue(pwd_getpwnam_mock.called)
        self.assertTrue(os_path_isfile_mock.called)
        self.assertTrue(backup_mock.called)
        self.assertTrue(os_path_basename_mock.called)
        self.assertTrue(inject_key_single_mock.called)

    @mock.patch("moduletests.src.openssh.inject_key_single", side_effect=[True])
    @mock.patch("os.path.basename", side_effect=["test", "test"])
    @mock.patch("moduletests.src.openssh.backup", side_effect=["test_backup_dir"])
    @mock.patch("os.path.isfile", side_effect=[True])
    @mock.patch("pwd.getpwnam")
    @mock.patch("os.path.isdir", side_effect=[False])
    @mock.patch("os.path.realpath", side_effect="/home/testuser")
    @mock.patch("glob.glob")
    def test_ssh_inject_key_all_not_isdir(self,
                                          glob_mock,
                                          os_path_realpath_mock,
                                          os_path_isdir_mock,
                                          pwd_getpwnam_mock,
                                          os_path_isfile_mock,
                                          backup_mock,
                                          os_path_basename_mock,
                                          inject_key_single_mock):
        glob_mock.return_value = ["/home/testuser"]
        pwd_getpwnam_mock.return_value.pw_uid = 1337
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(moduletests.src.openssh.inject_key_all("new_key",
                                                                   {"absolute": [], "relative": ["auth_keys"]},
                                                                   {},
                                                                   "backup_dir"))
        self.assertTrue(glob_mock.called)
        self.assertTrue(os_path_realpath_mock.called)
        self.assertTrue(os_path_isdir_mock.called)
        self.assertFalse(pwd_getpwnam_mock.called)
        self.assertFalse(os_path_isfile_mock.called)
        self.assertFalse(backup_mock.called)
        self.assertFalse(os_path_basename_mock.called)
        self.assertFalse(inject_key_single_mock.called)

    @mock.patch("moduletests.src.openssh.inject_key_single", side_effect=[True])
    @mock.patch("os.path.basename", side_effect=["test", "test"])
    @mock.patch("moduletests.src.openssh.backup", side_effect=["test_backup_dir"])
    @mock.patch("os.path.isfile", side_effect=[True])
    @mock.patch("pwd.getpwnam", side_effect=KeyError())
    @mock.patch("os.path.isdir", side_effect=[True])
    @mock.patch("os.path.realpath", side_effect="/home/testuser")
    @mock.patch("glob.glob")
    def test_ssh_inject_key_all_not_user(self,
                                         glob_mock,
                                         os_path_realpath_mock,
                                         os_path_isdir_mock,
                                         pwd_getpwnam_mock,
                                         os_path_isfile_mock,
                                         backup_mock,
                                         os_path_basename_mock,
                                         inject_key_single_mock):
        glob_mock.return_value = ["/home/testuser"]
        self.assertTrue(moduletests.src.openssh.inject_key_all("new_key",
                                                               {"absolute": [], "relative": ["auth_keys"]},
                                                               {},
                                                               "backup_dir"))
        self.assertTrue(glob_mock.called)
        self.assertTrue(os_path_realpath_mock.called)
        self.assertTrue(os_path_isdir_mock.called)
        self.assertTrue(pwd_getpwnam_mock.called)
        self.assertFalse(os_path_isfile_mock.called)
        self.assertFalse(backup_mock.called)
        self.assertTrue(os_path_basename_mock.called)
        self.assertFalse(inject_key_single_mock.called)

    @mock.patch("moduletests.src.openssh.inject_key_single", side_effect=[True])
    @mock.patch("os.path.basename", side_effect=["test", "test"])
    @mock.patch("moduletests.src.openssh.backup", side_effect=["test_backup_dir"])
    @mock.patch("os.path.isfile", side_effect=[False])
    @mock.patch("pwd.getpwnam")
    @mock.patch("os.path.isdir", side_effect=[True])
    @mock.patch("os.path.realpath", side_effect="/home/testuser")
    @mock.patch("glob.glob")
    def test_ssh_inject_key_all_not_file(self,
                                         glob_mock,
                                         os_path_realpath_mock,
                                         os_path_isdir_mock,
                                         pwd_getpwnam_mock,
                                         os_path_isfile_mock,
                                         backup_mock,
                                         os_path_basename_mock,
                                         inject_key_single_mock):
        glob_mock.return_value = ["/home/testuser"]
        pwd_getpwnam_mock.return_value.pw_uid = 1337
        self.assertTrue(moduletests.src.openssh.inject_key_all("new_key",
                                                               {"absolute": [], "relative": ["auth_keys"]},
                                                               {},
                                                               "backup_dir"))
        self.assertTrue(glob_mock.called)
        self.assertTrue(os_path_realpath_mock.called)
        self.assertTrue(os_path_isdir_mock.called)
        self.assertTrue(pwd_getpwnam_mock.called)
        self.assertTrue(os_path_isfile_mock.called)
        self.assertFalse(backup_mock.called)
        self.assertTrue(os_path_basename_mock.called)
        self.assertFalse(inject_key_single_mock.called)

    @mock.patch("glob.glob", side_effect=[Exception("Test")])
    def test_ssh_inject_key_all_exception(self, glob_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(moduletests.src.openssh.inject_key_all("new_key",
                                                                    {"absolute": [], "relative": ["auth_keys"]},
                                                                    {},
                                                                    "backup_dir"))
        self.assertTrue(glob_mock.called)

    @mock.patch("moduletests.src.openssh.open", mock.mock_open(read_data="test_key1\ntest_key2\n"))
    @mock.patch("os.path.isfile", side_effect=[True])
    def test_ssh_inject_key_single_key(self, isfile_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(
                moduletests.src.openssh.inject_key_single(new_key="test_key", full_path_auth_keys="test"))
        self.assertTrue(isfile_mock.called)

    @mock.patch("moduletests.src.openssh.open", side_effect=OSError())
    @mock.patch("os.path.isfile", side_effect=[True])
    def test_ssh_inject_key_single_key_exception(self, isfile_mock, open_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(
                moduletests.src.openssh.inject_key_single(new_key="test_key", full_path_auth_keys="test"))
        self.assertTrue(isfile_mock.called)
        self.assertTrue(open_mock.called)

    @mock.patch("moduletests.src.openssh.open", mock.mock_open(read_data="test_key\ntest_key2\n"))
    @mock.patch("os.path.isfile", side_effect=[True])
    def test_ssh_inject_key_single_key_already_present(self, isfile_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(
                moduletests.src.openssh.inject_key_single(new_key="test_key", full_path_auth_keys="test"))
        self.assertTrue(isfile_mock.called)

    def test_ssh_inject_key_single_invalid_args(self):
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(moduletests.src.openssh.inject_key_single(new_key="", full_path_auth_keys="test"))
            self.assertFalse(moduletests.src.openssh.inject_key_single(new_key="test", full_path_auth_keys=""))

    @mock.patch("subprocess.check_output", side_effect=["debug2: load_server_config: filename /etc/ssh/sshd_config\n"])
    def test_ssh_get_config_file_path_found(self, check_output_mock):
        self.assertEqual(moduletests.src.openssh.get_config_file_path(), "/etc/ssh/sshd_config")
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output", side_effect="debug2:")
    def test_ssh_get_config_file_path_not_found(self, check_output_mock):
        with self.assertRaises(Exception) as ex:
            moduletests.src.openssh.get_config_file_path()
            self.assertEqual(ex, "Failed to obtain server configuration file path!")
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1,
                                                          "test",
                                                          "debug2: load_server_config: filename "
                                                          "/etc/ssh/sshd_config\n"))
    def test_ssh_get_config_file_path_cpe_found_load_server_config(self, check_output_mock):
        self.assertEqual(moduletests.src.openssh.get_config_file_path(), "/etc/ssh/sshd_config")
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1,
                                                          "test",
                                                          "/etc/ssh/sshd_config: No such file or directory\n"))
    def test_ssh_get_config_file_path_cpe_found_no_such(self, check_output_mock):
        self.assertEqual(moduletests.src.openssh.get_config_file_path(), "/etc/ssh/sshd_config")
        self.assertTrue(check_output_mock.called)

    @mock.patch("subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1,
                                                          "test",
                                                          "Some other error\n"))
    def test_ssh_get_config_file_path_cpe_not_found(self, check_output_mock):
        with self.assertRaises(Exception) as ex:
            moduletests.src.openssh.get_config_file_path()
            self.assertEqual(ex, "Failed to obtain server configuration file path!")
        self.assertTrue(check_output_mock.called)

    def test_ssh_parse_configuration(self):
        open_mock = mock.mock_open(read_data="key1 value1\n"
                                             "too many values\n"
                                             "# comment\n"
                                             "# duplicates skipped\n"
                                             "key1 value1\n"
                                             "HostKey file1\n"
                                             "HostKey file2\n"
                                             "HostKey file_a file_b\n"
                                             "AuthorizedKeysFile %h/skipped\n"
                                             "AuthorizedKeysFile %u/skipped\n"
                                             "AuthorizedKeysFile file3\n"
                                             "AuthorizedKeysFile file4\n"
                                             "AuthorizedKeysFile file5 file6\n")
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")

        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func
        with mock.patch("moduletests.src.openssh.open", open_mock):
            with contextlib.redirect_stdout(StringIO()):
                ret = moduletests.src.openssh.parse_configuration("path/should/not/matter")
                self.assertTrue(isinstance(ret, dict))
                self.assertEqual(ret, {"AuthorizedKeysFile": ["file3", "file4", "file5", "file6"],
                                       "HostKey": ["file1", "file2"],
                                       "key1": ["value1"]})

    @mock.patch("moduletests.src.openssh.open", side_effect=IOError())
    def test_ssh_parse_configuration_invalid_path(self, open_mock):
        with contextlib.redirect_stdout(StringIO()):
            ret = moduletests.src.openssh.parse_configuration("tools/moduletests/tests/test_ssh.py")
            self.assertTrue(isinstance(ret, dict))
            self.assertEqual(ret, {})
        self.assertTrue(open_mock.called)

    @mock.patch("glob.glob")
    @mock.patch("os.path.realpath", side_effect=["/home/testuser",
                                                 "/one/two/three/file1",
                                                 "/usr/secrets/file2",
                                                 "walkroot",
                                                 "/etc/ssh/walkfile1",
                                                 "/etc/ssh/walkfile2_key",
                                                 "/etc/ssh/walkdir",
                                                 "/etc/ssh/ssh_host_dsa_key"])
    @mock.patch("os.path.isdir", side_effect=[True, True, False])
    @mock.patch("pwd.getpwnam")
    @mock.patch("os.walk")
    @mock.patch("os.stat", get_mocked_stat)
    @mock.patch("os.path.isfile", side_effect=[True])
    def test_ssh_get_dag(self,
                         os_path_isfile_mock,
                         os_walk_mock,
                         pwd_getpwnam_mock,
                         os_path_isdir_mock,
                         os_path_realpath_mock,
                         glob_mock):
        os_walk_mock.return_value = (("walkroot", ("walkdir",), ("walkfile1", "walkfile2_key")),)
        pwd_getpwnam_mock.return_value = mock.Mock(pw_uid=0, pw_gid=0, pw_nam="testuser")
        glob_mock.return_value = ["/home/testuser"]
        self.problem.CONFIG_DICT["HOSTKEYS"] = ["/etc/ssh/ssh_host_dsa_key"]
        with contextlib.redirect_stdout(StringIO()):
            test_dag = moduletests.src.openssh.get_dag(self.problem.CONFIG_DICT)

        vertex_dict = {"missing_sshd": ["missing_config_file",
                                        "bad_mode_/etc/ssh/ssh_host_dsa_key",
                                        "bad_uid_/etc/ssh/ssh_host_dsa_key"],
                       "bad_mode_/etc/ssh/ssh_host_dsa_key": [],
                       "bad_uid_/etc/ssh/ssh_host_dsa_key": [],

                       "missing_config_file": ["bad_config_options"],
                       "bad_config_options": ["missing_priv_sep_dir",
                                              "duplicate_keyfile_lines"],
                       "missing_priv_sep_dir":
                           ["missing_host_keys",
                            "bad_mode_/var/empty/sshd",
                            "bad_uid_/var/empty/sshd"],
                       "missing_host_keys": ["missing_priv_sep_user"],
                       "missing_priv_sep_user": [],
                       "bad_mode_/var/empty/sshd": [],
                       "bad_uid_/var/empty/sshd": [],

                       "missing_dir_/home":
                           ["bad_uid_/home",
                            "bad_mode_/home",
                            "missing_dir_/home/testuser"],
                       "bad_uid_/home": [],
                       "bad_mode_/home": [],

                       "duplicate_keyfile_lines":
                           ["missing_dir_/home",
                            "missing_dir_/one"],
                       "missing_dir_/home/testuser":
                           ["bad_mode_/home/testuser",
                            "bad_uid_/home/testuser",
                            "missing_dir_/home/testuser/.ssh",
                            "missing_key_/home/testuser/.keyfile1"],
                       "bad_uid_/home/testuser": [],
                       "bad_mode_/home/testuser": [],

                       "missing_dir_/home/testuser/.ssh":
                           ["bad_mode_/home/testuser/.ssh",
                            "bad_uid_/home/testuser/.ssh",
                            "missing_key_/home/testuser/.ssh/authorized_keys"],
                       "bad_uid_/home/testuser/.ssh": [],
                       "bad_mode_/home/testuser/.ssh": [],

                       "missing_key_/home/testuser/.ssh/authorized_keys":
                           ["bad_mode_/home/testuser/.ssh/authorized_keys",
                            "bad_uid_/home/testuser/.ssh/authorized_keys"],
                       "bad_uid_/home/testuser/.ssh/authorized_keys": [],
                       "bad_mode_/home/testuser/.ssh/authorized_keys": [],

                       "missing_key_/home/testuser/.keyfile1":
                           ["bad_mode_/home/testuser/.keyfile1",
                            "bad_uid_/home/testuser/.keyfile1"],
                       "bad_mode_/home/testuser/.keyfile1": [],
                       "bad_uid_/home/testuser/.keyfile1": [],

                       "missing_dir_/one":
                           ["bad_uid_/one",
                            "bad_mode_/one",
                            "missing_dir_/one/two"],
                       "bad_uid_/one": [],
                       "bad_mode_/one": [],

                       "missing_dir_/one/two":
                           ["bad_uid_/one/two",
                            "bad_mode_/one/two",
                            "missing_dir_/one/two/three"],
                       "bad_uid_/one/two": [],
                       "bad_mode_/one/two": [],

                       "missing_dir_/one/two/three":
                           ["bad_uid_/one/two/three",
                            "bad_mode_/one/two/three",
                            "missing_key_/one/two/three/file1"],
                       "bad_uid_/one/two/three": [],
                       "bad_mode_/one/two/three": [],

                       "missing_key_/one/two/three/file1":
                           ["bad_uid_/one/two/three/file1",
                            "bad_mode_/one/two/three/file1"],
                       "bad_uid_/one/two/three/file1": [],
                       "bad_mode_/one/two/three/file1": [],

                       "bad_mode_/etc/ssh": [],
                       "bad_mode_/etc/ssh/walkdir": [],
                       "bad_mode_/etc/ssh/walkfile1": [],
                       "bad_mode_/etc/ssh/walkfile2_key": [],
                       "bad_uid_/etc/ssh": [],
                       "bad_uid_/etc/ssh/walkdir": [],
                       "bad_uid_/etc/ssh/walkfile1": [],
                       "bad_uid_/etc/ssh/walkfile2_key": []}

        self.assertEqual(len(test_dag), 46)
        self.assertEqual(set(test_dag.vertices.keys()), set(vertex_dict.keys()))
        for key in vertex_dict:
            self.assertEqual(set(test_dag.vertices[key]), set(vertex_dict[key]))

        self.assertTrue(os_walk_mock.called)
        self.assertTrue(pwd_getpwnam_mock.called)
        self.assertTrue(os_path_isfile_mock.called)
        self.assertTrue(os_path_isdir_mock.called)
        self.assertTrue(os_path_realpath_mock.called)
        self.assertTrue(glob_mock.called)

    @mock.patch("glob.glob")
    @mock.patch("os.path.realpath", side_effect=["/home/testuser",
                                                 "/home/testuser",
                                                 "/home/testuser2",
                                                 "/home/testuser2",
                                                 "/etc/ssh/walkroot",
                                                 "/etc/ssh/walkfile1",
                                                 "/etc/ssh/walkdir",
                                                 "/etc/ssh/ssh_host_dsa_key",
                                                 "/etc/ssh/ssh_host_dsa_key"])
    @mock.patch("os.path.isdir", side_effect=[False, True])
    @mock.patch("pwd.getpwnam", side_effect=KeyError())
    @mock.patch("os.walk")
    @mock.patch("os.stat")
    @mock.patch("os.path.islink", side_effect=[True, True])
    @mock.patch("os.path.isfile", side_effect=[False, True])
    def test_ssh_get_dag_skips(self,
                               os_path_isfile_mock,
                               os_path_islink_mock,
                               os_stat_mock,
                               os_walk_mock,
                               pwd_getpwnam_mock,
                               os_path_isdir_mock,
                               os_path_realpath_mock,
                               glob_mock):
        os_stat_mock.return_value = mock.Mock(st_dev=0, st_ino=1)
        os_walk_mock.return_value = (("walkroot", ("walkdir",), ("walkfile1",)),)
        glob_mock.return_value = ["/home/testuser", "/home/testuser2"]
        self.problem.CONFIG_DICT["HOSTKEYS"] = ["/etc/ssh/ssh_host_dsa_key", "/etc/ssh/ssh_host_dsa_key"]
        self.problem.CONFIG_DICT["AUTH_KEYS"]["absolute"] = []

        with contextlib.redirect_stdout(StringIO()):
            test_dag = moduletests.src.openssh.get_dag(self.problem.CONFIG_DICT)

        vertex_dict = {"missing_sshd": ["missing_config_file"],
                       "missing_config_file": ["bad_config_options"],
                       "bad_config_options": ["missing_priv_sep_dir",
                                              "duplicate_keyfile_lines"],
                       "duplicate_keyfile_lines": [],
                       "missing_priv_sep_dir": ["missing_host_keys",
                                                "bad_uid_/var/empty/sshd",
                                                "bad_mode_/var/empty/sshd"],
                       "missing_host_keys": ["missing_priv_sep_user"],
                       "missing_priv_sep_user": [],
                       "bad_mode_/etc/ssh": [],
                       "bad_uid_/etc/ssh": [],
                       "bad_uid_/var/empty/sshd": [],
                       "bad_mode_/var/empty/sshd": []}

        self.assertEqual(len(test_dag), 11)
        self.assertEqual(set(test_dag.vertices.keys()), set(vertex_dict.keys()))
        for key in vertex_dict:
            self.assertEqual(set(test_dag.vertices[key]), set(vertex_dict[key]))

        self.assertTrue(os_stat_mock.called)
        self.assertTrue(os_walk_mock.called)
        self.assertTrue(pwd_getpwnam_mock.called)
        self.assertTrue(os_path_isfile_mock.called)
        self.assertTrue(os_path_islink_mock.called)
        self.assertTrue(os_path_isdir_mock.called)
        self.assertTrue(os_path_realpath_mock.called)
        self.assertTrue(glob_mock.called)

    def test_ssh_get_output_status_failure(self):
        v1 = moduletests.src.openssh.Vertex("v1", moduletests.src.openssh.Problem(state="UNCHECKED",
                                                                                  item_type="File",
                                                                                  item="v1 item",
                                                                                  value="v1 value",
                                                                                  value_str="v1 value_str",
                                                                                  info_msg="v1 info_msg",
                                                                                  check=self.return_true,
                                                                                  check_msg="v1 check_msg",
                                                                                  fix_msg="v1 fix_msg",
                                                                                  fix=self.return_true))
        v2 = moduletests.src.openssh.Vertex("v2", moduletests.src.openssh.Problem(state="FAILURE",
                                                                                  item_type="File",
                                                                                  item="v2 item",
                                                                                  value="v2 value",
                                                                                  value_str="v2 value_str",
                                                                                  info_msg="v2 info_msg",
                                                                                  check=self.return_true,
                                                                                  check_msg="v2 check_msg",
                                                                                  fix_msg="v2 fix_msg",
                                                                                  fix=self.return_true))
        self.dag.add_vertex(v1)
        self.dag.add_vertex(v2)
        self.assertEqual(moduletests.src.openssh.get_output_status("/test/log/dir", self.dag),
                         "[FAILURE] Improper configuration of one or more OpenSSH components.\n"
                         "-- SSH may deny access to users when improperly configured.\n"
                         "-- FAILURE     v2 info_msg: v2 item\n"
                         "--             v2 fix_msg\n"
                         "-- Unable to check 1 items due to dependent check failures:\n"
                         "   UNCHECKED   v1 info_msg: v1 item\n"
                         "\n"
                         "Please view /test/log/dir/run/ssh.log for additional details.\n")

    def test_ssh_get_output_status_fix_failed(self):
        v1 = moduletests.src.openssh.Vertex("v1", moduletests.src.openssh.Problem(state="FIX_FAILED",
                                                                                  item_type="File",
                                                                                  item="v1 item",
                                                                                  value="v1 value",
                                                                                  value_str="v1 value_str",
                                                                                  info_msg="v1 info_msg",
                                                                                  check=self.return_true,
                                                                                  check_msg="v1 check_msg",
                                                                                  fix_msg="v1 fix_msg",
                                                                                  fix=self.return_true))
        self.dag.add_vertex(v1)
        self.assertEqual(moduletests.src.openssh.get_output_status("/test/log/dir", self.dag),
                         "[FAILURE] Failed to remediate one or more problems.\n"
                         "-- SSH may deny access to users when improperly configured.\n"
                         "-- FIX_FAILED  v1 info_msg: v1 item\n"
                         "--             v1 fix_msg\n"
                         "\n"
                         "Please view /test/log/dir/run/ssh.log for additional details.\n")

    def test_ssh_get_output_status_warn(self):
        v1 = moduletests.src.openssh.Vertex("v1", moduletests.src.openssh.Problem(state="WARN",
                                                                                  item_type="File",
                                                                                  item="v1 item",
                                                                                  value="v1 value",
                                                                                  value_str="v1 value_str",
                                                                                  info_msg="v1 info_msg",
                                                                                  check=self.return_true,
                                                                                  check_msg="v1 check_msg",
                                                                                  fix_msg="v1 fix_msg",
                                                                                  fix=self.return_true))
        self.dag.add_vertex(v1)
        self.assertEqual(moduletests.src.openssh.get_output_status("/test/log/dir", self.dag),
                         "[WARN] Unable to fully validate one or more OpenSSH components.\n"
                         "-- Configuration could not be fully validated.\n"
                         "-- WARN        v1 info_msg: v1 item\n"
                         "--             v1 fix_msg\n"
                         "\n"
                         "Please view /test/log/dir/run/ssh.log for additional details.\n")

    def test_ssh_get_output_status_success(self):
        v1 = moduletests.src.openssh.Vertex("v1", moduletests.src.openssh.Problem(state="FIXED",
                                                                                  item_type="File",
                                                                                  item="v1 item",
                                                                                  value="v1 value",
                                                                                  value_str="v1 value_str",
                                                                                  info_msg="v1 info_msg",
                                                                                  check=self.return_true,
                                                                                  check_msg="v1 check_msg",
                                                                                  fix_msg="v1 fix_msg",
                                                                                  fix=self.return_true))
        self.dag.add_vertex(v1)
        self.assertEqual(moduletests.src.openssh.get_output_status("/test/log/dir", self.dag),
                         "[SUCCESS] All configuration checks passed or all detected problems fixed.\n"
                         "-- FIXED       v1 info_msg: v1 item\n"
                         "\n"
                         "Please view /test/log/dir/run/ssh.log for additional details.\n")

    def test_ssh_get_output_status_empty_dag(self):
        self.assertEqual(moduletests.src.openssh.get_output_status("/test/log/dir", self.dag),
                         "[WARN] the problem graph was empty!\n-- The configuration was not validated.\n"
                         "\n"
                         "Please view /test/log/dir/run/ssh.log for additional details.\n")

    @mock.patch("subprocess.check_output", side_effect=["     /var/run/sshd\n"
                                                        "             chroot(2) directory used by sshd during "
                                                        "privilege separation in the pre-authentication phase.  The "
                                                        "directory should not contain any files and"])
    def test_ssh_get_privilege_separation_dir_subprocess_found_plaintext(self, subprocess_mock):
        self.assertEqual(moduletests.src.openssh.get_privilege_separation_dir(), "/var/run/sshd")
        self.assertTrue(subprocess_mock.called)

    @mock.patch("subprocess.check_output", side_effect=["     /var/run/sshd\n"
                                                        "             chroot(2) directory used by "
                                                        "s\x08ss\x08sh\x08hd\x08d during "
                                                        "privilege separation in the pre-authentication phase.  The "
                                                        "directory should not contain any files and"])
    def test_ssh_get_privilege_separation_dir_subprocess_found_escaped_chars(self, subprocess_mock):
        self.assertEqual(moduletests.src.openssh.get_privilege_separation_dir(), "/var/run/sshd")
        self.assertTrue(subprocess_mock.called)

    @mock.patch("subprocess.check_output", side_effect=["These are not\nthe lines you are looking for\n"])
    def test_ssh_get_privilege_separation_dir_subprocess_not_found(self, subprocess_mock):
        with self.assertRaises(Exception) as ex:
            moduletests.src.openssh.get_privilege_separation_dir()
            self.assertEqual(ex, "Failed to obtain privilege separation directory path!")
        self.assertTrue(subprocess_mock.called)

    @mock.patch("subprocess.check_output", side_effect=OSError(2, "No such file or directory"))
    @mock.patch("os.path.exists", side_effect=[False, False, True])
    def test_ssh_get_privilege_separation_dir_subprocess_exception_found(self, os_mock, subprocess_mock):
        self.assertEqual(moduletests.src.openssh.get_privilege_separation_dir(), "/var/run/sshd")
        self.assertTrue(os_mock.called)
        self.assertTrue(subprocess_mock.called)

    @mock.patch("subprocess.check_output", side_effect=OSError(2, "No such file or directory"))
    @mock.patch("os.path.exists", side_effect=[False, False, False])
    def test_ssh_get_privilege_separation_dir_subprocess_exception_not_found(self, os_mock, subprocess_mock):
        with self.assertRaises(Exception) as ex:
            moduletests.src.openssh.get_privilege_separation_dir()
            self.assertEqual(ex, "Failed to obtain privilege separation directory path!")
        self.assertTrue(os_mock.called)
        self.assertTrue(subprocess_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem.setup_run_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.get_dag", return_value=moduletests.src.openssh.DirectedAcyclicGraph())
    @mock.patch("moduletests.src.openssh.DirectedAcyclicGraph.topological_solve", side_effect=[True])
    @mock.patch("moduletests.src.openssh.get_output_status", side_effect=[True])
    def test_ssh_run(self,
                     get_output_status_mock,
                     topological_solve_mock,
                     get_dag_mock,
                     setup_run_vars_mock,
                     setup_config_vars_mock):
        with contextlib.redirect_stdout(StringIO()):
            moduletests.src.openssh.run()
        self.assertTrue(get_output_status_mock.called)
        self.assertTrue(topological_solve_mock.called)
        self.assertTrue(get_dag_mock.called)
        self.assertTrue(setup_run_vars_mock.called)
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[OSError])
    @mock.patch("moduletests.src.openssh.Problem.setup_run_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.get_dag", return_value=moduletests.src.openssh.DirectedAcyclicGraph())
    @mock.patch("moduletests.src.openssh.DirectedAcyclicGraph.topological_solve", side_effect=[True])
    @mock.patch("moduletests.src.openssh.get_output_status", side_effect=[True])
    def test_ssh_run_config_vars_oserror(self,
                                         get_output_status_mock,
                                         topological_solve_mock,
                                         get_dag_mock,
                                         setup_run_vars_mock,
                                         setup_config_vars_mock):
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(moduletests.src.openssh.run())
        self.assertTrue(get_output_status_mock.called)
        self.assertTrue(topological_solve_mock.called)
        self.assertTrue(get_dag_mock.called)
        self.assertTrue(setup_run_vars_mock.called)
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[ValueError])
    def test_ssh_unhandled_exception(self, setup_config_vars_mock):
        output = StringIO()
        with contextlib.redirect_stdout(output):
            self.assertFalse(moduletests.src.openssh.run())
        self.assertTrue("[WARN] module generated an exception" in output.getvalue())
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem.setup_run_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.key_injection_driver", side_effect=[True])
    def test_ssh_run_injectkeyonly_success(self,
                                           key_injection_driver_mock,
                                           setup_run_vars_mock,
                                           setup_config_vars_mock):
        self.problem.CONFIG_DICT["REMEDIATE"] = True
        self.problem.CONFIG_DICT["INJECT_KEY_ONLY"] = True
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(moduletests.src.openssh.run())
        self.assertTrue(key_injection_driver_mock.called)
        self.assertTrue(setup_run_vars_mock.called)
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem.setup_run_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.key_injection_driver", side_effect=[False])
    def test_ssh_run_injectkeyonly_failure(self,
                                           key_injection_driver_mock,
                                           setup_run_vars_mock,
                                           setup_config_vars_mock):
        self.problem.CONFIG_DICT["REMEDIATE"] = True
        self.problem.CONFIG_DICT["INJECT_KEY_ONLY"] = True
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(moduletests.src.openssh.run())
        self.assertTrue(key_injection_driver_mock.called)
        self.assertTrue(setup_run_vars_mock.called)
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem.setup_run_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.key_injection_driver", side_effect=[False])
    def test_ssh_run_injectkey_failure(self,
                                       key_injection_driver_mock,
                                       setup_run_vars_mock,
                                       setup_config_vars_mock):
        self.problem.CONFIG_DICT["REMEDIATE"] = True
        self.problem.CONFIG_DICT["INJECT_KEY"] = True
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(moduletests.src.openssh.run())
        self.assertTrue(key_injection_driver_mock.called)
        self.assertTrue(setup_run_vars_mock.called)
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem.setup_run_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.get_dag", return_value=moduletests.src.openssh.DirectedAcyclicGraph())
    @mock.patch("moduletests.src.openssh.DirectedAcyclicGraph.topological_solve", side_effect=[True])
    @mock.patch("moduletests.src.openssh.get_output_status", side_effect=[True])
    def test_ssh_run_injectkey_missing_remediate(self,
                                                 get_output_status_mock,
                                                 topological_solve_mock,
                                                 get_dag_mock,
                                                 setup_run_vars_mock,
                                                 setup_config_vars_mock):
        self.problem.CONFIG_DICT["REMEDIATE"] = False
        self.problem.CONFIG_DICT["INJECT_KEY"] = True
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(moduletests.src.openssh.run())
        self.assertTrue(get_output_status_mock.called)
        self.assertTrue(topological_solve_mock.called)
        self.assertTrue(get_dag_mock.called)
        self.assertTrue(setup_run_vars_mock.called)
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem.setup_run_vars", side_effect=[True])
    def test_ssh_run_injectkeyonly_missing_remediate(self,
                                                     setup_run_vars_mock,
                                                     setup_config_vars_mock):
        self.problem.CONFIG_DICT["REMEDIATE"] = False
        self.problem.CONFIG_DICT["INJECT_KEY_ONLY"] = True
        with contextlib.redirect_stdout(StringIO()):
            self.assertFalse(moduletests.src.openssh.run())
        self.assertTrue(setup_run_vars_mock.called)
        self.assertTrue(setup_config_vars_mock.called)

    @mock.patch("moduletests.src.openssh.Problem.setup_config_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.Problem.setup_run_vars", side_effect=[True])
    @mock.patch("moduletests.src.openssh.key_injection_driver", side_effect=[True])
    @mock.patch("moduletests.src.openssh.get_dag", return_value=moduletests.src.openssh.DirectedAcyclicGraph())
    @mock.patch("moduletests.src.openssh.DirectedAcyclicGraph.topological_solve", side_effect=[True])
    @mock.patch("moduletests.src.openssh.get_output_status", side_effect=[True])
    def test_ssh_run_injectkey_success(self,
                                       get_output_status_mock,
                                       topological_solve_mock,
                                       get_dag_mock,
                                       key_injection_driver_mock,
                                       setup_run_vars_mock,
                                       setup_config_vars_mock):
        self.problem.CONFIG_DICT["REMEDIATE"] = True
        self.problem.CONFIG_DICT["INJECT_KEY"] = True
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(moduletests.src.openssh.run())
        self.assertTrue(get_output_status_mock.called)
        self.assertTrue(topological_solve_mock.called)
        self.assertTrue(get_dag_mock.called)
        self.assertTrue(key_injection_driver_mock.called)
        self.assertTrue(setup_run_vars_mock.called)
        self.assertTrue(setup_config_vars_mock.called)
