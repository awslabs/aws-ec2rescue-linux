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
Unit tests for "main" module. Primarily uses curses.ungetch to simulate keyboard input.
Note that the input buffer acts like a stack so when reading the tests, keep in mind that the characters
are in reverse order.
"""
import curses
import logging
import os
import re
import sys
import unittest

try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

import boto3
import mock
import moto
import requests
import responses

import ec2rlcore.awshelpers
import ec2rlcore.backup
import ec2rlcore.console_out
import ec2rlcore.main
import ec2rlcore.module
import ec2rlcore.moduledir
import ec2rlcore.prediag
import ec2rlcore.s3upload

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib

# builtins was named __builtin__ in Python 2 so accommodate the change for the purposes of mocking the open call
if sys.version_info >= (3,):
    builtins_name = "builtins"
else:
    builtins_name = "__builtin__"


def simple_return(*args, **kwargs):
    return True


class TestMain(unittest.TestCase):
    """Testing class for "main" unit tests."""
    argv_backup = sys.argv
    _callp = sys.argv[0]
    if not os.path.isabs(_callp):
        _callp = os.path.abspath(_callp)
    if os.path.isdir(_callp):
        callpath = _callp
    else:
        callpath = os.path.split(_callp)[0]
    ec2rl = None
    PROGRAM_VERSION = "1.0.0"

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def setUp(self, main_log_handler_mock, debug_log_handler_mock, mkdir_mock):
        sys.argv = ["test/modules/not_a_real_file", "run", "--abc=def"]
        os.chdir(self.callpath)
        os.environ["EC2RL_SUDO"] = "False"
        os.environ["EC2RL_DISTRO"] = "alami"
        os.environ["EC2RL_NET_DRIVER"] = "ixgbevf"
        os.environ["EC2RL_VIRT_TYPE"] = "hvm"
        with contextlib.redirect_stdout(StringIO()):
            self.ec2rl = ec2rlcore.main.Main(debug=True, full_init=True)
            self.ec2rl.full_init()

        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

        self.output = StringIO()

    def tearDown(self):
        sys.argv = self.argv_backup
        del os.environ["EC2RL_SUDO"]
        del os.environ["EC2RL_DISTRO"]
        del os.environ["EC2RL_NET_DRIVER"]
        del os.environ["EC2RL_VIRT_TYPE"]
        logging.shutdown()
        # Reset the global variable that tracks the first module execution
        ec2rlcore.console_out._first_module = True
        self.output.close()

    @moto.mock_ec2
    def setup_ec2(self):
        """Setting up for usage, including moto environment"""
        ec2 = boto3.client("ec2", region_name="us-east-1")

        response = ec2.run_instances(
            ImageId="ami-deadbeef",
            MinCount=1,
            MaxCount=1,
            KeyName="deadbeef",
            InstanceType="m4.16xlarge",
        )
        instance = response["Instances"][0]
        instanceid = instance["InstanceId"]

        return instanceid

    def test_main_instantiation(self):
        """Test creating an instance of Main."""
        self.assertEqual(self.ec2rl.constraint, {"class": ["gather", "diagnose", "collect"],
                                                 "distro": ["ubuntu", "alami", "rhel", "suse", "centos"],
                                                 "domain": ["os", "net", "performance", "application"],
                                                 "software": ["ip", "arptables", "awk", "atop", "biolatency",
                                                              "biosnoop", "biotop", "bitesize", "cachestat", "dcsnoop",
                                                              "dcstat", "execsnoop", "ext4dist", "ext4slower",
                                                              "filelife", "fileslower", "filetop", "gethostlatency",
                                                              "hardirqs", "killsnoop", "opensnoop", "pidspersec",
                                                              "runqlat", "slabratetop", "softirqs", "statsnoop",
                                                              "syncsnoop", "tcpaccept", "tcpconnect", "tcpconnlat",
                                                              "tcplife", "tcpretrans", "tcptop", "vfscount",
                                                              "vfsstat", "xfsdist", "xfsslower", "collectl", "dmesg",
                                                              "dig", "blkid", "ebtables", "cat", "ethtool", "gcore",
                                                              "iostat", "iptables", "journalctl", "ltrace", "mpstat",
                                                              "nc", "ss", "netstat", "nping", "nstat", "lsof", "perf",
                                                              "ps", "sar", "slabtop", "stat", "strace", "tcpdump",
                                                              "traceroute", "top", "vmstat", "w"],
                                                 "perfimpact": ["False", "True"]})
        self.assertEqual(self.ec2rl.options.global_args["abc"], "def")
        self.assertFalse(self.ec2rl.options.per_module_args)
        self.assertEqual(len(self.ec2rl._modules), 112)
        self.assertEqual(len(self.ec2rl._prediags), 1)
        self.assertEqual(self.ec2rl._prediags[0].name, "ex")
        self.assertEqual(len(self.ec2rl._postdiags), 1)
        self.assertEqual(self.ec2rl._prediags[0].name, "ex")
        self.assertEqual(self.ec2rl.subcommand, "run")

    @mock.patch("os.mkdir", side_effect=simple_return)
    def test_main__setup_paths_absolute_path(self, mkdir_mock):
        """Test _setup_paths when the path in sys.argv is an absolute path."""
        sys.argv = [""]
        callpath = sys.argv[0]
        if not os.path.isabs(callpath):
            callpath = os.path.abspath(callpath)
        sys.argv = [callpath]
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        self.assertTrue(self.ec2rl._setup_write_paths())

        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[OSError(os.errno.EEXIST, "message"),
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return])
    def test_main__setup_paths_workdir_oserror_eexist(self, mkdir_mock):
        """"Test behavior when attempting to create WORKDIR when it already exists."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        self.assertTrue(self.ec2rl._setup_write_paths())
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         OSError(os.errno.EEXIST, "message"),
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return])
    def test_main__setup_paths_rundir_oserror_eexist(self, mkdir_mock):
        """"Test behavior when attempting to create RUNDIR when it already exists."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        self.assertTrue(self.ec2rl._setup_write_paths())
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         OSError(os.errno.EEXIST, "message"),
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return])
    def test_main__setup_paths_logdir_oserror_eexist(self, mkdir_mock):
        """"Test behavior when attempting to create LOGDIR when it already exists."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        self.assertTrue(self.ec2rl._setup_write_paths())
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         simple_return,
                                         OSError(os.errno.EEXIST, "message"),
                                         simple_return,
                                         simple_return,
                                         simple_return])
    def test_main__setup_paths_prediag_oserror_eexist(self, mkdir_mock):
        """"Test behavior when attempting to create the prediagnostic LOGDIR when it already exists."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        self.assertTrue(self.ec2rl._setup_write_paths())
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         OSError(os.errno.EEXIST, "message"),
                                         simple_return,
                                         simple_return])
    def test_main__setup_paths_run_oserror_eexist(self, mkdir_mock):
        """"Test behavior when attempting to create the run LOGDIR when it already exists."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        self.assertTrue(self.ec2rl._setup_write_paths())
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         OSError(os.errno.EEXIST, "message"),
                                         simple_return])
    def test_main__setup_paths_post_oserror_eexist(self, mkdir_mock):
        """"Test behavior when attempting to create the postdiagnostic LOGDIR when it already exists."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        self.assertTrue(self.ec2rl._setup_write_paths())
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         OSError(os.errno.EEXIST, "message")])
    def test_main__setup_paths_gather_oserror_eexist(self, mkdir_mock):
        """"Test behavior when attempting to create GATHEREDDIR when it already exists."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        self.assertTrue(self.ec2rl._setup_write_paths())
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=OSError())
    def test_main__setup_paths_workdir(self, mkdir_mock):
        """"Test behavior when attempting to create WORKDIR and an unexpected error occurs."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        with self.assertRaises(ec2rlcore.main.MainDirectoryError):
            self.ec2rl._setup_write_paths()
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         OSError()])
    def test_main__setup_paths_rundir(self, mkdir_mock):
        """"Test behavior when attempting to create RUNDIR and an unexpected error occurs."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        with self.assertRaises(ec2rlcore.main.MainDirectoryError):
            self.ec2rl._setup_write_paths()
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         OSError()])
    def test_main__setup_paths_logdir(self, mkdir_mock):
        """"Test behavior when attempting to create LOGDIR and an unexpected error occurs."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        with self.assertRaises(ec2rlcore.main.MainDirectoryError):
            self.ec2rl._setup_write_paths()
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         simple_return,
                                         OSError()])
    def test_main__setup_paths_prediag(self, mkdir_mock):
        """"Test behavior when attempting to create the prediagnostic LOGDIR and an unexpected error occurs."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        with self.assertRaises(ec2rlcore.main.MainDirectoryError):
            self.ec2rl._setup_write_paths()
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         OSError()])
    def test_main__setup_paths_run(self, mkdir_mock):
        """"Test behavior when attempting to create the run LOGDIR and an unexpected error occurs."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        with self.assertRaises(ec2rlcore.main.MainDirectoryError):
            self.ec2rl._setup_write_paths()
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         OSError()])
    def test_main__setup_paths_post(self, mkdir_mock):
        """"Test behavior when attempting to create the postdiagnostic LOGDIR and an unexpected error occurs."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        with self.assertRaises(ec2rlcore.main.MainDirectoryError):
            self.ec2rl._setup_write_paths()
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=[simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         simple_return,
                                         OSError()])
    def test_main__setup_paths_gather(self, mkdir_mock):
        """"Test behavior when attempting to create GATHEREDDIR and an unexpected error occurs."""
        self.ec2rl._write_initialized = False  # Force re-initialization of writing for test
        with self.assertRaises(ec2rlcore.main.MainDirectoryError):
            self.ec2rl._setup_write_paths()
        self.assertTrue(mkdir_mock.called)

    def test_main_get_help_default(self):
        """Test that the help function returns a help string when no subcommand is given."""
        output = self.ec2rl.get_help()
        self.assertIsInstance(output, str)
        self.assertEqual(len(output), 8437)
        self.assertTrue(output.startswith("ec2rl:  A framework for executing diagnostic and troubleshooting\n"))
        self.assertTrue(output.endswith("bug                    - enables debug level logging\n"))

    def test_main_get_help_run_subcommand(self):
        """Test that the help function returns a help string for a valid subcommand (run)."""
        output = self.ec2rl.get_help("run")
        self.assertIsInstance(output, str)
        self.assertEqual(len(output), 2540)
        self.assertTrue(output.startswith("run:\n    SYNOPSIS:\n        ec2rl run [--only-"))
        self.assertTrue(output.endswith("to run in parallel. The default is 10.\n\n"))

    def test_main_get_help_invalid_subcommand(self):
        """Test that the help function the default help string for invalid subcommands."""
        self.assertEqual(self.ec2rl.get_help("not_a_real_subcommand"), self.ec2rl.get_help())

    def test_main_list(self):
        """Test that the list subcommand returns True when complete and outputs the expected number of characters."""
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.list())
        self.assertTrue(self.output.getvalue().startswith("Here is a list of available modules that apply to the curr"))
        self.assertTrue(self.output.getvalue().endswith("=MODULEa ... MODULEx] [--only-domains=DOMAINa ... DOMAINx]\n"))
        self.assertEqual(len(self.output.getvalue()), 14533)

    def test_main_list_nonapplicable_modules(self):
        """
        Disable the "xennetrocket" module then test that the list subcommand returns True when complete and outputs
        the expected number of characters.
        """
        for module_obj in self.ec2rl._modules:
            if module_obj.name == "xennetrocket":
                module_obj.applicable = False
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.list())
        self.assertTrue(self.output.getvalue().startswith("Here is a list of available modules that apply to the curr"))
        self.assertTrue(self.output.getvalue().endswith("=MODULEa ... MODULEx] [--only-domains=DOMAINa ... DOMAINx]\n"))
        self.assertFalse(re.search(r"xennetrocket", self.output.getvalue()))
        self.assertEqual(len(self.output.getvalue()), 14410)

    def test_main_help(self):
        """Test that help returns True and get_help's output matches the expected length."""
        sys.argv = ["ec2rl", "help"]
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.help())
        self.assertTrue(self.output.getvalue().startswith("ec2rl:  A framework for executing diagnostic and troublesh"))
        self.assertTrue(self.output.getvalue().endswith("- enables debug level logging\n\n"))
        self.assertEqual(len(self.output.getvalue()), 8438)

    def test_main_help_module(self):
        """Test output from a single module."""
        self.ec2rl.options.global_args["onlymodules"] = "aptlog"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.help())

        self.assertEqual(self.output.getvalue(), "aptlog:\nCollect apt log files\nRequires sudo: True\n")
        del self.ec2rl.options.global_args["onlymodules"]

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main_onlydomain_double_add(self, main_log_handler_mock, debug_log_handler_mock, mkdir_mock):
        """Test that specifying the same domain twice doesn't add it to the list twice."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "help", "--only-domains=net,net"]
        ec2rl = ec2rlcore.main.Main(debug=True, full_init=True)

        self.assertEqual(ec2rl.options.domains_to_run, ["net"])
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main_onlyclasses_double_add(self, main_log_handler_mock, debug_log_handler_mock, mkdir_mock):
        """Test that specifying the same class twice doesn't add it to the list twice."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "help", "--only-classes=diagnose,diagnose"]
        ec2rl = ec2rlcore.main.Main(debug=True, full_init=True)

        self.assertEqual(ec2rl.options.classes_to_run, ["diagnose"])
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main_help_domain(self, main_log_handler_mock, mkdir_mock):
        """Test help output for a domain of modules."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "help", "--only-domains=net,asdf"]
        ec2rl = ec2rlcore.main.Main(full_init=True)

        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl.help())

        # Check that the length of the help message matches the expected value
        self.assertEqual(len(self.output.getvalue()), 5826)
        self.assertTrue(self.output.getvalue().startswith("arpcache:\nDetermines if aggressive arp caching is enabled"))
        self.assertTrue(self.output.getvalue().endswith("ackets to drop due to discarded skbs\nRequires sudo: False\n"))
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main_help_class(self, main_log_handler_mock, mkdir_mock):
        """Test help output for a class of modules."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "help", "--only-classes=diagnose,asdf"]
        ec2rl = ec2rlcore.main.Main(full_init=True)

        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl.help())

        # Check that the length of the help message matches the expected value
        self.assertEqual(len(self.output.getvalue()), 1777)
        self.assertTrue(self.output.getvalue().startswith("arpcache:\nDetermines if aggressive arp caching is enabled"))
        self.assertTrue(self.output.getvalue().endswith("ackets to drop due to discarded skbs\nRequires sudo: False\n"))
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main_default_subcommand(self, main_log_handler_mock, debug_log_handler_mock, mkdir_mock):
        """Test that the default subcommand is set."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path]
        ec2rl = ec2rlcore.main.Main(debug=True, full_init=True)

        self.assertEqual(ec2rl.subcommand, "default_help")
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    def test_main_help_subcommand(self):
        """Test help output for the 'run' subcommand."""
        sys.argv = ["ec2rl", "help", "run"]
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.help())

        # Check that the length of the help message matches the expected value
        self.assertEqual(len(self.output.getvalue()), 2541)
        self.assertTrue(self.output.getvalue().startswith("run:\n    SYNOPSIS:\n        ec2rl run [--only-modules=MOD"))
        self.assertTrue(self.output.getvalue().endswith("to run in parallel. The default is 10.\n\n\n"))

    def test_main_help_module_subcommand_and_invalid(self):
        """
        Test help output for an arg that does not match any condition as well as the 'list' subcommand
        and the 'arpcache' module.
        """
        sys.argv = ["ec2rl", "help", "doesnotmatchanything", "arpcache", "list", ]
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.help())

        # Check that the length of the help message matches the expected value
        self.assertEqual(len(self.output.getvalue()), 595)
        self.assertTrue(self.output.getvalue().startswith("arpcache:\nDetermines if aggressive arp caching is enabled"))
        self.assertTrue(self.output.getvalue().endswith("                       specified comma delimited list\n\n\n"))

    def test_main_version(self):
        """Test output from the version subcommand."""
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.version())

        # Check that the length of the version message matches the expected value
        self.assertEqual(len(self.output.getvalue()), 272 + len(self.PROGRAM_VERSION))
        self.assertTrue(self.output.getvalue().startswith("ec2rl {}\nCopyright 201".format(self.PROGRAM_VERSION)))
        self.assertTrue(self.output.getvalue().endswith("TIES OR CONDITIONS OF ANY KIND, either express or implied.\n"))

    def test_main_bugreport(self):
        """Test output from the bugreport subcommand."""
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.bug_report())

        # Example output:
        # ec2rl 1.0.0
        # ubuntu, 4.4.0-83-generic
        # Python 3.5.2, /usr/bin/python3
        regex_str = r"^ec2rl\ [0-9]+\.[0-9]+\.[0-9]+.*\n(ubuntu|suse|rhel|alami),\ [0-9]+\.[0-9]+\.[0-9]+.*\n" \
                    r"Python\ [0-9]+\.[0-9]+\.[0-9]+.*,\ /.*\n$"

        self.assertTrue(re.match(regex_str, self.output.getvalue()))

    def test_main__setup_environ(self):
        """Test that environment variables are setup as expected."""
        self.ec2rl.options.global_args["perfimpact"] = "true"
        self.ec2rl._setup_environ()
        self.assertEqual(os.environ["EC2RL_PERFIMPACT"], "True")
        del self.ec2rl.options.global_args["perfimpact"]

        self.ec2rl._setup_environ()
        self.assertEqual(os.environ["EC2RL_PERFIMPACT"], "False")
        self.assertEqual(os.environ["EC2RL_WORKDIR"], "/var/tmp/ec2rl")
        self.assertTrue(os.environ["EC2RL_RUNDIR"].startswith("/var/tmp/ec2rl/"))
        self.assertTrue(os.environ["EC2RL_LOGDIR"].startswith("/var/tmp/ec2rl/"))
        self.assertTrue(os.environ["EC2RL_LOGDIR"].endswith("/mod_out"))
        self.assertTrue(os.environ["EC2RL_GATHEREDDIR"].startswith("/var/tmp/ec2rl/"))
        self.assertTrue(os.environ["EC2RL_GATHEREDDIR"].endswith("/gathered_out"))
        self.assertTrue(os.environ["EC2RL_CALLPATH"].endswith("test/modules"))
        self.assertTrue(re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}_[0-9]{2}_[0-9]{2}.[0-9]{6}$",
                                 os.environ["EC2RL_SPECDIR"]))

    @mock.patch("{}.open".format(builtins_name), new_callable=mock.mock_open())
    def test_main_save_config(self, open_mock):
        """Test that save_config() returns True and the configuration file would have been opened."""
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.save_config())
        self.assertEqual(len(self.output.getvalue()), 129)
        self.assertTrue(re.match(r"^\n----------\[Configuration File\]----------\n\nConfiguration file saved:\n"
                                 r"/var/tmp/ec2rl/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}_[0-9]{2}_[0-9]{2}.[0-9]{6}"
                                 r"/configuration.cfg\n$",
                                 self.output.getvalue()))
        self.assertTrue(open_mock.called)

    @mock.patch("{}.open".format(builtins_name), new_callable=mock.mock_open())
    def test_main_menu_config(self, open_mock):
        """Test that the menu configurator functions."""
        self.ec2rl.options.global_args["abc"] = "def"
        curses.initscr()
        # main menu -> exit
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        # Modules menu -> main menu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        # atop -> Modules menu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        # atop -> period = 1
        curses.ungetch("\n")
        curses.ungetch("1")
        curses.ungetch("\n")
        # Modules menu -> atop
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        # main menu -> Modules menu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        # Global menu -> main menu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        # Global -> concurrency -> 2
        curses.ungetch("\n")
        curses.ungetch("2")
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        # Global menu -> only-classes menu
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        # unselect "collect"
        curses.ungetch(" ")
        curses.ungetch("\n")
        # main menu -> Global menu
        curses.ungetch("\n")
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.menu_config())
        self.assertTrue(re.match(r"^\n----------\[Configuration File\]----------\n\nConfiguration file saved:\n"
                                 r"/var/tmp/ec2rl/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}_[0-9]{2}_[0-9]{2}.[0-9]{6}"
                                 r"/configuration.cfg\n$",
                                 self.output.getvalue()))
        self.assertEqual(len(self.output.getvalue()), 129)
        self.assertTrue(open_mock.called)
        self.assertEqual(self.ec2rl.options.global_args["abc"], "def")
        self.assertEqual(self.ec2rl.options.global_args["concurrency"], "2")
        self.assertEqual(self.ec2rl.options.global_args["onlyclasses"], "diagnose,gather")
        self.assertEqual(self.ec2rl.options.per_module_args["atop"]["period"], "1")

    @responses.activate
    @mock.patch("logging.FileHandler")
    @mock.patch("ec2rlcore.options.Options.write_config", side_effect=simple_return)
    @mock.patch("os.chdir", side_effect=simple_return)
    @mock.patch("shutil.copyfile", side_effect=simple_return)
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.main.Main._run_prediagnostics", side_effect=[simple_return])
    def test_main_menu_config_run(self,
                                  prediag_mock,
                                  main_log_handler_mock,
                                  debug_log_handler_mock,
                                  mkdir_mock,
                                  copyfile_mock,
                                  chdir_mock,
                                  write_config_mock,
                                  logging_fh_mock):
        """Test running ec2rl from the menu."""
        # Setup the instance of Main
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "menu-config"]
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_run_test = ec2rlcore.main.Main(debug=True, full_init=True)

        ec2rl_run_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._postdiags = ec2rlcore.moduledir.ModuleDir(module_path)

        # We don't need to run pre/post modules for this test
        ec2rl_run_test._prediags = []
        ec2rl_run_test._postdiags = []

        # Setup the input buffer for curses to grab from
        curses.initscr()
        # main menu -> run
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)
        curses.ungetch(curses.KEY_DOWN)

        with contextlib.redirect_stdout(self.output):
            ec2rl_run_test()
        self.assertTrue(self.output.getvalue().startswith("\n-----------[Backup  Creation]-----------\n\nNo backup op"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("-\n\nRunning Modules:\nxennetrocket\n\n-" in self.output.getvalue())
        self.assertEqual(len(self.output.getvalue()), 1635)

        self.assertTrue(prediag_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(copyfile_mock.called)
        self.assertTrue(chdir_mock.called)
        self.assertTrue(write_config_mock.called)
        self.assertTrue(logging_fh_mock.called)
        # The resulting subcommand should be "run"
        self.assertEqual(ec2rl_run_test.subcommand, "run")

    @mock.patch("ec2rlcore.main.Main.save_config", side_effect=[False])
    def test_main_menu_config_save_config_failed(self, mock_side_effect_function):
        """Test handling of a failed save_config() call."""
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        self.assertFalse(self.ec2rl.menu_config())
        self.assertTrue(mock_side_effect_function.called)

    @mock.patch("ec2rlcore.options.Options.write_config", side_effect=simple_return)
    def test_main_menu_config_global_module_removal(self, write_config_mock):
        """Test removal of a module named Global."""
        original_length = len(self.ec2rl._modules)
        global_mod = ec2rlcore.module.get_module("test/modules/bad_mod.d/global.yaml")
        self.ec2rl._modules.append(global_mod)
        self.assertNotEqual(len(self.ec2rl._modules), original_length)
        curses.initscr()
        curses.ungetch("\n")
        curses.ungetch(curses.KEY_RIGHT)
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.menu_config())
        self.assertEqual(len(self.output.getvalue()), 129)
        self.assertTrue(re.match(r"^\n----------\[Configuration File\]----------\n\nConfiguration file saved:\n"
                                 r"/var/tmp/ec2rl/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}_[0-9]{2}_[0-9]{2}.[0-9]{6}"
                                 r"/configuration.cfg\n$",
                                 self.output.getvalue()))
        self.assertEqual(len(self.ec2rl._modules), original_length)
        self.assertTrue("Global" not in self.ec2rl._modules)
        self.assertTrue(write_config_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__run_prunemodules_only_modules(self,
                                                 main_log_handler_mock,
                                                 debug_log_handler_mock,
                                                 mkdir_mock):
        """Test that --only-modules=arpcache results in just that single module remaning after pruning."""
        # Test --only-modules=
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--only-modules=arpcache"]
        ec2rl_pruning_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_pruning_test._modules.validate_constraints_have_args(options=ec2rl_pruning_test.options,
                                                                   constraint=ec2rl_pruning_test.constraint,
                                                                   without_keys=["software",
                                                                                 "distro",
                                                                                 "sudo",
                                                                                 "requires_ec2"])

        ec2rl_pruning_test._run_prunemodules()

        self.assertEqual(len(ec2rl_pruning_test._modules), 1)
        self.assertEqual(ec2rl_pruning_test._modules[0].name, "arpcache")
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertEqual(len(ec2rl_pruning_test.prune_stats), 0, "Exactly 0 elements in prune stats")

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.prediag.which", side_effect=simple_return)
    def test_main__run_prunemodules_only_domains(self,
                                                 main_log_handler_mock,
                                                 debug_log_handler_mock,
                                                 mkdir_mock,
                                                 which_mock):
        """Test that --only-domains=os results the expected number of remaining modules after pruning.
        Note: this number is actually less than the total number of os modules because some will fail
        other prediagnostic checks."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--only-domains=os"]
        ec2rl_pruning_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_pruning_test._modules.validate_constraints_have_args(options=ec2rl_pruning_test.options,
                                                                   constraint=ec2rl_pruning_test.constraint,
                                                                   without_keys=["software",
                                                                                 "distro",
                                                                                 "sudo",
                                                                                 "requires_ec2"])
        ec2rl_pruning_test._run_prunemodules()
        self.assertEqual(len(ec2rl_pruning_test._modules), 6)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(which_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.prediag.which", side_effect=simple_return)
    def test_main__run_prunemodules_only_classes(self,
                                                 main_log_handler_mock,
                                                 debug_log_handler_mock,
                                                 mkdir_mock,
                                                 which_mock):
        """Test that --only-classes=diagnose results the expected number of remaining modules after pruning.
        Note: this number is actually less than the total number of diagnose modules because some will fail
        other prediagnostic checks."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--only-classes=diagnose"]

        ec2rl_pruning_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_pruning_test._modules.validate_constraints_have_args(options=ec2rl_pruning_test.options,
                                                                   constraint=ec2rl_pruning_test.constraint,
                                                                   without_keys=["software",
                                                                                 "distro",
                                                                                 "sudo",
                                                                                 "requires_ec2"])
        ec2rl_pruning_test._run_prunemodules()
        self.assertEqual(len(ec2rl_pruning_test._modules), 6)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(which_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__run_prunemodules_software_constraint(self,
                                                        main_log_handler_mock,
                                                        debug_log_handler_mock,
                                                        mkdir_mock):
        """Test that modules are pruned when the software constraint is not satisfied."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_pruning_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/test_main_multi_run_prunemodules_fakeexecutable")
        ec2rl_pruning_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_pruning_test._modules.validate_constraints_have_args(options=ec2rl_pruning_test.options,
                                                                   constraint=ec2rl_pruning_test.constraint,
                                                                   without_keys=["software",
                                                                                 "distro",
                                                                                 "sudo",
                                                                                 "requires_ec2"])

        self.assertEqual(len(ec2rl_pruning_test._modules), 1)
        the_module = ec2rl_pruning_test._modules[0]
        ec2rl_pruning_test._run_prunemodules()
        self.assertEqual(len(ec2rl_pruning_test._modules), 0)
        self.assertEqual(the_module.whyskipping,
                         "Requires missing/non-executable software 'hopefully_not_a_real_program_name'.")
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertEqual(len(ec2rl_pruning_test.prune_stats), 1, "Exactly 1 element in prune stats")
        self.assertEqual(ec2rl_pruning_test.prune_stats.get(ec2rlcore.module.SkipReason.MISSING_SOFTWARE, 0), 1,
                         "Prune stats counted 1 MISSING_SOFTWARE prune")

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__run_prunemodules_perfimpact_constraint(self,
                                                          main_log_handler_mock,
                                                          debug_log_handler_mock,
                                                          mkdir_mock):
        """Test that modules are pruned when the perfimpact constraint is not satisfied."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_pruning_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/test_main__run_prunemodules_perfimpact_constraint")
        ec2rl_pruning_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_pruning_test._modules.validate_constraints_have_args(options=ec2rl_pruning_test.options,
                                                                   constraint=ec2rl_pruning_test.constraint,
                                                                   without_keys=["software",
                                                                                 "distro",
                                                                                 "sudo",
                                                                                 "requires_ec2"])

        self.assertEqual(len(ec2rl_pruning_test._modules), 1)
        the_module = ec2rl_pruning_test._modules[0]
        ec2rl_pruning_test._run_prunemodules()
        self.assertEqual(len(ec2rl_pruning_test._modules), 0)
        self.assertEqual(the_module.whyskipping,
                         "Requires performance impact okay, but not given.")
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertEqual(len(ec2rl_pruning_test.prune_stats), 1, "Exactly 1 element in prune stats")
        self.assertEqual(ec2rl_pruning_test.prune_stats.get(ec2rlcore.module.SkipReason.PERFORMANCE_IMPACT, 0), 1,
                         "Prune stats counted 1 PERFORMANCE_IMPACT prune")

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__run_prunemodules_requires_ec2_constraint(self,
                                                            main_log_handler_mock,
                                                            debug_log_handler_mock,
                                                            mkdir_mock):
        """Test that modules are pruned when the ec2_required constraint is not satisfied."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--not-an-instance"]
        ec2rl_pruning_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/test_main__run_prunemodules_requires_ec2_constraint/")
        ec2rl_pruning_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_pruning_test._modules.validate_constraints_have_args(options=ec2rl_pruning_test.options,
                                                                   constraint=ec2rl_pruning_test.constraint,
                                                                   without_keys=["software",
                                                                                 "distro",
                                                                                 "sudo",
                                                                                 "requires_ec2"])

        self.assertEqual(len(ec2rl_pruning_test._modules), 1)
        the_module = ec2rl_pruning_test._modules[0]
        ec2rl_pruning_test._run_prunemodules()
        self.assertEqual(len(ec2rl_pruning_test._modules), 0)
        self.assertEqual(the_module.whyskipping,
                         "Module requires system be an EC2 instance.")
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertEqual(len(ec2rl_pruning_test.prune_stats), 0, "Exactly 0 elements in prune stats")

    @mock.patch("logging.FileHandler")
    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.prediag.check_root", side_effect=["True"])
    @mock.patch("ec2rlcore.prediag.get_distro", side_effect=["alami"])
    @mock.patch("ec2rlcore.prediag.get_net_driver", side_effect=["ixgbevf"])
    @mock.patch("ec2rlcore.prediag.get_virt_type", side_effect=["hvm"])
    @mock.patch("ec2rlcore.prediag.verify_metadata", side_effect=[True])
    def test_main__run_prediagnostics(self,
                                      verify_metadata_mock,
                                      get_virt_type_mock,
                                      get_net_driver_mock,
                                      get_distro_mock,
                                      check_root_mock,
                                      main_log_handler_mock,
                                      debug_log_handler_mock,
                                      mkdir_mock,
                                      makedirs_mock,
                                      logging_fh_mock):
        """Test that successfully running prediagnostics returns True."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/pre.d")
        ec2rl_prediag_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        self.assertTrue(ec2rl_prediag_test._run_prediagnostics())
        self.assertNotEqual(os.environ["EC2RL_VIRT_TYPE"], "non-virtualized")
        self.assertTrue(verify_metadata_mock.called)
        self.assertTrue(get_virt_type_mock.called)
        self.assertTrue(get_net_driver_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(makedirs_mock.called)
        self.assertTrue(logging_fh_mock.called)

    @mock.patch("logging.FileHandler")
    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.prediag.check_root", side_effect=["True"])
    @mock.patch("ec2rlcore.prediag.get_distro", side_effect=["alami"])
    @mock.patch("ec2rlcore.prediag.get_net_driver", side_effect=["ixgbevf"])
    @mock.patch("ec2rlcore.prediag.get_virt_type", side_effect=["hvm"])
    @mock.patch("ec2rlcore.prediag.verify_metadata", side_effect=[True])
    def test_main__run_prediagnostics_failure(self,
                                              verify_metadata_mock,
                                              get_virt_type_mock,
                                              get_net_driver_mock,
                                              get_distro_mock,
                                              check_root_mock,
                                              main_log_handler_mock,
                                              debug_log_handler_mock,
                                              mkdir_mock,
                                              makedirs_mock,
                                              logging_fh_mock):
        """Test that successfully running prediagnostics returns True."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/bad_pre.d")
        ec2rl_prediag_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        with self.assertRaises(ec2rlcore.main.MainPrediagnosticFailure):
            self.assertTrue(ec2rl_prediag_test._run_prediagnostics())
        self.assertNotEqual(os.environ["EC2RL_VIRT_TYPE"], "non-virtualized")
        self.assertTrue(verify_metadata_mock.called)
        self.assertTrue(get_virt_type_mock.called)
        self.assertTrue(get_net_driver_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(makedirs_mock.called)
        self.assertTrue(logging_fh_mock.called)

    @mock.patch("logging.FileHandler")
    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.prediag.check_root", side_effect=["True"])
    @mock.patch("ec2rlcore.prediag.get_distro", side_effect=["alami"])
    @mock.patch("ec2rlcore.prediag.get_net_driver", side_effect=["ixgbevf"])
    def test_main__run_prediagnostics_notaninstance(self,
                                                    get_net_driver_mock,
                                                    get_distro_mock,
                                                    check_root_mock,
                                                    main_log_handler_mock,
                                                    debug_log_handler_mock,
                                                    mkdir_mock,
                                                    makedirs_mock,
                                                    logging_fh_mock):
        """
        Test that successfully running prediagnostics returns True and sets the EC2RL_VIRT_TYPE properly 
        when the arg --not-an-instance is given.
        """
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        sys.argv = ["ec2rl", "run", "--not-an-instance"]
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/pre.d")
        ec2rl_prediag_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        self.assertTrue(ec2rl_prediag_test._run_prediagnostics())
        self.assertEqual(os.environ["EC2RL_VIRT_TYPE"], "non-virtualized")
        self.assertTrue(get_net_driver_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(makedirs_mock.called)
        self.assertTrue(logging_fh_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.prediag.check_root", side_effect=["True"])
    @mock.patch("ec2rlcore.prediag.get_distro", side_effect=["alami"])
    @mock.patch("ec2rlcore.prediag.get_net_driver", side_effect=["ixgbevf"])
    @mock.patch("ec2rlcore.prediag.verify_metadata", side_effect=[False])
    def test_main__run_prediagnostics_metadata_fail(self,
                                                    verify_metadata_mock,
                                                    get_net_driver_mock,
                                                    get_distro_mock,
                                                    check_root_mock,
                                                    main_log_handler_mock,
                                                    debug_log_handler_mock,
                                                    mkdir_mock):
        """Test that _run_prediagnostics() raises MainPrediagnosticFailure when the metadata server is inaccessible."""
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/pre.d")
        ec2rl_prediag_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        with self.assertRaises(ec2rlcore.main.MainPrediagnosticFailure):
            with contextlib.redirect_stdout(self.output):
                ec2rl_prediag_test._run_prediagnostics()
        self.assertEqual(self.output.getvalue(), "prediagnostic/verify_metadata: cannot reach metadata server\n")

        self.assertTrue(verify_metadata_mock.called)
        self.assertTrue(get_net_driver_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.prediag.check_root", side_effect=["False"])
    @mock.patch("ec2rlcore.prediag.get_distro", side_effect=["alami"])
    @mock.patch("ec2rlcore.prediag.get_net_driver", side_effect=["ixgbevf"])
    @mock.patch("ec2rlcore.prediag.get_virt_type", side_effect=["hvm"])
    @mock.patch("ec2rlcore.prediag.verify_metadata", side_effect=[True])
    def test_main__run_prediagnostics_module_not_applicable(self,
                                                            verify_metadata_mock,
                                                            get_virt_type_mock,
                                                            get_net_driver_mock,
                                                            get_distro_mock,
                                                            check_root_mock,
                                                            main_log_handler_mock,
                                                            debug_log_handler_mock,
                                                            mkdir_mock):
        """Test that _run_prediagnostics() successfully completes when the only module isn't applicable."""
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/pre.d")
        ec2rl_prediag_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_prediag_test._prediags[0].applicable = False
        self.assertTrue(ec2rl_prediag_test._run_prediagnostics())
        self.assertTrue(verify_metadata_mock.called)
        self.assertTrue(get_virt_type_mock.called)
        self.assertTrue(get_net_driver_mock.called)
        self.assertTrue(get_distro_mock.called)
        self.assertTrue(check_root_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__run_backup_no_options(self, main_log_handler_mock, debug_log_handler_mock, mkdir_mock):
        """Test that _run_backup() runs (doesn"t necessarily do anything though) when no backup options are set."""
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_prediag_test._run_backup())
        self.assertEqual(self.output.getvalue(), "\n-----------[Backup  Creation]-----------\n\nNo backup option"
                                                 " selected. Please consider backing up your volumes or instance\n")
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @responses.activate
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @moto.mock_ec2
    def test_main__run_backup_allvolumes(self, main_log_handler_mock, debug_log_handler_mock, mkdir_mock):
        """Test that _run_backup() runs correctly when allvolumes are specified."""
        instanceid = self.setup_ec2()
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/placement/availability-zone",
                      body="us-east-1a", status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body=instanceid,
                      status=200)
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_prediag_test.options.global_args["backup"] = "allvolumes"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_prediag_test._run_backup())
        self.assertTrue(re.match(r"^\n-----------\[Backup\s{2}Creation\]-----------\n\nCreating snapshot "
                                 r"snap-[a-z0-9]{8} for volume vol-[a-z0-9]{8}\n$",
                                 self.output.getvalue(), re.M))

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @responses.activate
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @moto.mock_ec2
    def test_main__run_backup_ami(self, main_log_handler_mock, debug_log_handler_mock, mkdir_mock):
        """Test that _run_backup() runs correctly when ami is specified."""
        instanceid = self.setup_ec2()
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/placement/availability-zone",
                      body="us-east-1a", status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body=instanceid,
                      status=200)
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_prediag_test.options.global_args["backup"] = "ami"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_prediag_test._run_backup())
        self.assertTrue(re.match(r"^\n-----------\[Backup\s{2}Creation\]-----------\n\nCreating AMI "
                                 r"ami-[a-z0-9]{8} for i-[a-z0-9]{8}\n$",
                                 self.output.getvalue(), re.M))
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__run_backup_empty_backup_value(self,
                                                 main_log_handler_mock,
                                                 debug_log_handler_mock,
                                                 mkdir_mock):
        """Test that an invalid backup value raise an MainInvalidVolumeSpecificationError exception."""
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_prediag_test.options.global_args["backup"] = ""
        with self.assertRaises(ec2rlcore.main.MainInvalidVolumeSpecificationError):
            with contextlib.redirect_stdout(self.output):
                ec2rl_prediag_test._run_backup()
        self.assertEqual(self.output.getvalue(), "\n-----------[Backup  Creation]-----------\n\nImproper specification"
                                                 " of volumes. Please verify you have specified a volume"
                                                 " such as vol-xxxxx.\n")

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @responses.activate
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @moto.mock_ec2
    def test_main__run_backup_invalid_ebs_volumeid_value(self,
                                                         main_log_handler_mock,
                                                         debug_log_handler_mock,
                                                         mkdir_mock):
        """Test that an invalid EBS volume name raise a ClientError exception."""
        instanceid = self.setup_ec2()
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/placement/availability-zone",
                      body="us-east-1a", status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body=instanceid,
                      status=200)
        ec2rl_prediag_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_prediag_test.options.global_args["backup"] = "vol-1"
        with self.assertRaises(ec2rlcore.backup.BackupClientError):
            with contextlib.redirect_stdout(self.output):
                ec2rl_prediag_test._run_backup()
        self.assertEqual(self.output.getvalue(), "\n-----------[Backup  Creation]-----------\n\n")

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main_missing_subcommand(self, main_log_handler_mock, mkdir_mock):
        """Test that the short help message is printed when no subcommand is provided."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path]
        ec2rl_run_test = ec2rlcore.main.Main()
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_run_test())
        self.assertTrue(self.output.getvalue().startswith("ec2rl:  A framework for executing diagnostic and troublesh"))
        self.assertTrue(self.output.getvalue().endswith("ion in a bug report\n\n\nec2rl: missing subcommand operand\n"))
        self.assertEqual(len(self.output.getvalue()), 1066)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    def test_main_upload_missing_uploaddirectory(self):
        """Test how the missing --upload-directory arg is handled."""
        with self.assertRaises(ec2rlcore.main.MainMissingRequiredArgument):
            self.ec2rl.upload()

    def test_main_upload_missing_url_argument(self):
        """Test how the missing [--presigned-url, --support-url] arg is handled."""
        self.ec2rl.options.global_args["uploaddirectory"] = "."
        with self.assertRaises(ec2rlcore.main.MainMissingRequiredArgument):
            self.ec2rl.upload()
        del self.ec2rl.options.global_args["uploaddirectory"]

    def test_main_upload_with_invalid_unparseable_support_url(self):
        """Test how invalid support URLs are handled in the upload subcommand."""
        self.ec2rl.options.global_args["uploaddirectory"] = "."
        self.ec2rl.options.global_args["supporturl"] = "http://fakeurl.com/"
        with self.assertRaises(ec2rlcore.s3upload.S3UploadUrlParsingFailure):
            self.ec2rl.upload()
        del self.ec2rl.options.global_args["uploaddirectory"]
        del self.ec2rl.options.global_args["supporturl"]

    def test_main_upload_with_invalid_parseable_support_url(self):
        """Test that valid support URLs result in success."""
        self.ec2rl.options.global_args["uploaddirectory"] = "."
        self.ec2rl.options.global_args["supporturl"] = \
            "https://aws-support-uploader.s3.amazonaws.com/uploader?account-id=123&case-id=567" \
            "&expiration=1486577795&key=789"
        with self.assertRaises(ec2rlcore.s3upload.S3UploadGetPresignedURLError):
            self.ec2rl.upload()
        del self.ec2rl.options.global_args["uploaddirectory"]
        del self.ec2rl.options.global_args["supporturl"]

    @mock.patch("{}.__import__".format(builtins_name), side_effect=ImportError)
    def test_main_upload_missing_sni_support(self, mock_import):
        """Test that missing SSL SNI support raises a MainUploadMissingSNISupport exception."""
        self.ec2rl.options.global_args["uploaddirectory"] = "."
        self.ec2rl.options.global_args["presignedurl"] = "abc"
        with self.assertRaises(ec2rlcore.main.MainUploadMissingSNISupport):
            self.ec2rl.upload()
        self.assertTrue(mock_import.called)
        del self.ec2rl.options.global_args["uploaddirectory"]
        del self.ec2rl.options.global_args["presignedurl"]

    @mock.patch("ec2rlcore.s3upload.make_tarfile", side_effect=simple_return)
    @mock.patch("ec2rlcore.s3upload.s3upload", side_effect=simple_return)
    def test_main_upload_file_removal_failure(self, mock_s3upload, mock_make_tarfile):
        """Test handling of an error while trying to remove a non-existent or otherwise inaccessible tarball."""
        self.ec2rl.options.global_args["uploaddirectory"] = "."
        self.ec2rl.options.global_args["presignedurl"] = "abc"
        with self.assertRaises(ec2rlcore.main.MainFileRemovalError):
            self.ec2rl.upload()
        self.assertTrue(mock_s3upload.called)
        self.assertTrue(mock_make_tarfile.called)
        del self.ec2rl.options.global_args["uploaddirectory"]
        del self.ec2rl.options.global_args["presignedurl"]

    @mock.patch("ec2rlcore.s3upload.os.remove", side_effect=simple_return)
    @mock.patch("ec2rlcore.s3upload.s3upload", side_effect=simple_return)
    @mock.patch("ec2rlcore.s3upload.make_tarfile", side_effect=simple_return)
    def test_main_upload_success(self, mock_make_tarfile, mock_s3upload, mock_os_remove):
        """Test that upload returns True when the upload was successful."""
        self.ec2rl.options.global_args["uploaddirectory"] = "."
        self.ec2rl.options.global_args["presignedurl"] = "abc"
        self.assertTrue(self.ec2rl.upload())
        self.assertTrue(mock_make_tarfile.called)
        self.assertTrue(mock_s3upload.called)
        self.assertTrue(mock_os_remove.called)
        del self.ec2rl.options.global_args["uploaddirectory"]
        del self.ec2rl.options.global_args["presignedurl"]

    @mock.patch("os.remove", side_effect=simple_return)
    @mock.patch("{}.open".format(builtins_name), new_callable=mock.mock_open())
    @mock.patch("ec2rlcore.s3upload.make_tarfile", side_effect=simple_return)
    @responses.activate
    def test_main_upload_with_invalid_presigned_url(self, make_tarfile_mock, open_mock, remove_mock):
        """Test how invalid presigned URLs are handled in the upload subcommand."""
        responses.add(responses.PUT, "http://fakeurl.com", status=403)
        self.ec2rl.options.global_args["uploaddirectory"] = "."
        self.ec2rl.options.global_args["presignedurl"] = "http://fakeurl.com/"
        with self.assertRaises(ec2rlcore.s3upload.S3UploadResponseError):
            with contextlib.redirect_stdout(self.output):
                self.ec2rl.upload()
        self.assertEqual(self.output.getvalue(), "ERROR: Upload failed.  Received response 403\n")
        self.assertTrue(make_tarfile_mock.called)
        self.assertTrue(open_mock.called)
        self.assertTrue(remove_mock.called)
        del self.ec2rl.options.global_args["uploaddirectory"]
        del self.ec2rl.options.global_args["presignedurl"]

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @responses.activate
    def test_main__summary_single_diagnose_unknown(self,
                                                   main_log_handler_mock,
                                                   debug_log_handler_mock,
                                                   mkdir_mock):
        """Test that _summary() returns True and test its output when the run_status is UNKNOWN."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_summary_test._modules[0].run_status_details = ["--item1", "--item2"]

        ec2rl_summary_test._modules[0].run_status = "UNKNOWN"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n----------[Diagnostic Results]----------\n\nmodule predi"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("unknown:                     1" in self.output.getvalue())

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @responses.activate
    def test_main__summary_single_diagnose_success(self,
                                                   main_log_handler_mock,
                                                   debug_log_handler_mock,
                                                   mkdir_mock):
        """Test that _summary() returns True and test its output when the run_status is SUCCESS."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_summary_test._modules[0].run_status_details = ["--item1", "--item2"]

        ec2rl_summary_test._modules[0].run_status = "SUCCESS"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n----------[Diagnostic Results]----------\n\nmodule predi"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("successes:                   1" in self.output.getvalue())

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @responses.activate
    def test_main__summary_single_diagnose_failure(self,
                                                   main_log_handler_mock,
                                                   debug_log_handler_mock,
                                                   mkdir_mock):
        """Test that _summary() returns True and test its output when the run_status is FAILURE."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_summary_test._modules[0].run_status_details = ["--item1", "--item2"]

        ec2rl_summary_test._modules[0].run_status = "FAILURE"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n----------[Diagnostic Results]----------\n\nmodule predi"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("failures:                    1" in self.output.getvalue())

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @responses.activate
    def test_main__summary_single_diagnose_warn(self,
                                                main_log_handler_mock,
                                                debug_log_handler_mock,
                                                mkdir_mock):
        """Test that _summary() returns True and test its output when the run_status is WARN."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_summary_test._modules[0].run_status_details = ["--item1", "--item2"]

        ec2rl_summary_test._modules[0].run_status = "WARN"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n----------[Diagnostic Results]----------\n\nmodule predi"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("warnings:                    1" in self.output.getvalue())

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @responses.activate
    def test_main__summary_single_diagnose_empty_run_status_details(self,
                                                                    main_log_handler_mock,
                                                                    debug_log_handler_mock,
                                                                    mkdir_mock):
        """Test that _summary() returns True and prints the expected amount of characters."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_summary_test._modules[0].run_status_details = []

        ec2rl_summary_test._modules[0].run_status = "UNKNOWN"
        output = StringIO()
        with contextlib.redirect_stdout(output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertEqual(len(output.getvalue()), 1154)
        self.assertTrue(output.getvalue().startswith("\n----------[Diagnostic Results]----------\n\nmodule "
                                                     "prediagnostic/xennetroc"))
        self.assertTrue(output.getvalue().endswith(
            "form/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        output.close()

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @responses.activate
    def test_main__summary_single_collect_unknown(self,
                                                  main_log_handler_mock,
                                                  debug_log_handler_mock,
                                                  mkdir_mock):
        """
        Test that _summary() returns True for a single collect module when there are no diagnose modules run
        and test its output when the run_status is UNKNOWN.
        """
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_collect/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        # Removing the "diagnose" key will test the path that skips the diagnose-related messages
        del ec2rl_summary_test.modules.class_map["diagnose"]

        ec2rl_summary_test._modules[0].run_status = "UNKNOWN"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n--------------[Run  Stats]--------------\n\nTotal module"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("collect\' modules run:           1" in self.output.getvalue())

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @responses.activate
    def test_main__summary_single_collect_success(self,
                                                  main_log_handler_mock,
                                                  debug_log_handler_mock,
                                                  mkdir_mock):
        """
        Test that _summary() returns True for a single collect module when there are no diagnose modules run
        and test its output when the run_status is SUCCESS.
        """
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_collect/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        # Removing the "diagnose" key will test the path that skips the diagnose-related messages
        del ec2rl_summary_test.modules.class_map["diagnose"]

        ec2rl_summary_test._modules[0].run_status = "SUCCESS"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n--------------[Run  Stats]--------------\n\nTotal module"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("collect\' modules run:           1" in self.output.getvalue())

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @responses.activate
    def test_main__summary_single_collect_failure(self,
                                                  main_log_handler_mock,
                                                  debug_log_handler_mock,
                                                  mkdir_mock):
        """
        Test that _summary() returns True for a single collect module when there are no diagnose modules run
        and test its output when the run_status is FAILURE.
        """
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_collect/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        # Removing the "diagnose" key will test the path that skips the diagnose-related messages
        del ec2rl_summary_test.modules.class_map["diagnose"]

        ec2rl_summary_test._modules[0].run_status = "FAILURE"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n--------------[Run  Stats]--------------\n\nTotal module"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("collect\' modules run:           1" in self.output.getvalue())

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @responses.activate
    def test_main__summary_single_diagnose_warn(self,
                                                main_log_handler_mock,
                                                debug_log_handler_mock,
                                                mkdir_mock):
        """
        Test that _summary() returns True for a single collect module when there are no diagnose modules run
        and test its output when the run_status is WARN.
        """
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_collect/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        # Removing the "diagnose" key will test the path that skips the diagnose-related messages
        del ec2rl_summary_test.modules.class_map["diagnose"]

        ec2rl_summary_test._modules[0].run_status = "WARN"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n--------------[Run  Stats]--------------\n\nTotal module"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("collect\' modules run:           1" in self.output.getvalue())

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("logging.FileHandler")
    @mock.patch("os.makedirs", side_effect=simple_return)
    def test_main__run_postdiagnostics(self, makedirs_mock, logging_fh_mock):
        """Test that postdiagnostics run."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        self.assertTrue(self.ec2rl._run_postdiagnostics())
        # Flip the applicable boolean value
        self.ec2rl._postdiags[0].applicable = not self.ec2rl._postdiags[0].applicable
        self.assertTrue(self.ec2rl._run_postdiagnostics())
        # Set the applicable boolean value back how it was originally
        self.ec2rl._postdiags[0].applicable = not self.ec2rl._postdiags[0].applicable
        self.assertTrue(makedirs_mock.called)
        self.assertTrue(logging_fh_mock.called)

    def test_main___call__(self):
        """Test running the instance of Main and check the length of its output to stdout."""
        original_subcommand = self.ec2rl.subcommand
        self.ec2rl.subcommand = "help"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl())
        self.assertTrue(self.output.getvalue().startswith("ec2rl:  A framework for executing diagnostic and troublesh"))
        self.assertTrue(self.output.getvalue().endswith("- enables debug level logging\n\n"))
        self.assertEqual(len(self.output.getvalue()), 8438)
        self.ec2rl.subcommand = original_subcommand

    def test_main___call__subcommand_arg(self):
        """Test running the instance of Main with a subcommand arg and check the length of its output to stdout."""

        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl(subcommand="help"))
        self.assertTrue(self.output.getvalue().startswith("ec2rl:  A framework for executing diagnostic and troublesh"))
        self.assertTrue(self.output.getvalue().endswith("- enables debug level logging\n\n"))
        self.assertEqual(len(self.output.getvalue()), 8438)

    @responses.activate
    @mock.patch("logging.FileHandler")
    @mock.patch("ec2rlcore.options.Options.write_config", side_effect=simple_return)
    @mock.patch("os.chdir", side_effect=simple_return)
    @mock.patch("shutil.copyfile", side_effect=simple_return)
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.main.Main._run_prediagnostics", side_effect=[simple_return])
    def test_main_run(self,
                      prediag_mock,
                      main_log_handler_mock,
                      debug_log_handler_mock,
                      mkdir_mock,
                      copyfile_mock,
                      chdir_mock,
                      write_config_mock,
                      logging_fh_mock):
        """Test running the instance of Main."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_run_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_run_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._postdiags = ec2rlcore.moduledir.ModuleDir(module_path)

        # We don't need to run pre/post modules for this test
        ec2rl_run_test._prediags = []
        ec2rl_run_test._postdiags = []

        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_run_test())
        self.assertTrue(self.output.getvalue().startswith("\n-----------[Backup  Creation]-----------\n\nNo backup op"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("Total modules run:               1" in self.output.getvalue())
        self.assertEqual(len(self.output.getvalue()), 1635)

        self.assertTrue(prediag_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(copyfile_mock.called)
        self.assertTrue(chdir_mock.called)
        self.assertTrue(write_config_mock.called)
        self.assertTrue(logging_fh_mock.called)

    @responses.activate
    @mock.patch("logging.FileHandler")
    @mock.patch("ec2rlcore.options.Options.write_config", side_effect=simple_return)
    @mock.patch("os.chdir", side_effect=simple_return)
    @mock.patch("shutil.copyfile", side_effect=simple_return)
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.main.Main._run_prediagnostics", side_effect=[simple_return])
    def test_main_run_single_binary(self,
                                    prediag_mock,
                                    main_log_handler_mock,
                                    debug_log_handler_mock,
                                    mkdir_mock,
                                    copyfile_mock,
                                    chdir_mock,
                                    write_config_mock,
                                    logging_fh_mock):
        """Test running the instance of Main with a single binary module."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        module_path = os.path.join(self.callpath, "test/modules/single_binary/mod.d/")
        ec2rl_run_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_run_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._postdiags = ec2rlcore.moduledir.ModuleDir(module_path)

        # We don't need to run pre/post modules for this test
        ec2rl_run_test._prediags = []
        ec2rl_run_test._postdiags = []

        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_run_test())
        self.assertTrue(self.output.getvalue().startswith("\n-----------[Backup  Creation]-----------\n\nNo backup op"))
        self.assertTrue(self.output.getvalue().endswith(
            "V_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("Total modules run:               1" in self.output.getvalue())
        self.assertTrue(ec2rl_run_test._modules[0].processoutput == "[SUCCESS] Hello, world!\n")
        self.assertEqual(len(self.output.getvalue()), 1558)

        self.assertTrue(prediag_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(copyfile_mock.called)
        self.assertTrue(chdir_mock.called)
        self.assertTrue(write_config_mock.called)
        self.assertTrue(logging_fh_mock.called)

    @responses.activate
    @mock.patch("ec2rlcore.main.Main._run_backup", side_effect=simple_return)
    @mock.patch("logging.FileHandler")
    @mock.patch("ec2rlcore.options.Options.write_config", side_effect=simple_return)
    @mock.patch("os.chdir", side_effect=simple_return)
    @mock.patch("shutil.copyfile", side_effect=simple_return)
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.main.Main._run_prediagnostics", side_effect=[simple_return])
    def test_main_run_notaninstance(self,
                                    prediag_mock,
                                    main_log_handler_mock,
                                    debug_log_handler_mock,
                                    mkdir_mock,
                                    copyfile_mock,
                                    chdir_mock,
                                    write_config_mock,
                                    logging_fh_mock,
                                    backup_mock):
        """Test running the instance of Main. Verify that _run_backup is not called."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--not-an-instance"]
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_run_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_run_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._postdiags = ec2rlcore.moduledir.ModuleDir(module_path)

        # We don't need to run pre/post modules for this test
        ec2rl_run_test._prediags = []
        ec2rl_run_test._postdiags = []

        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_run_test())
        self.assertTrue(self.output.getvalue().startswith(
            "\n----------[Configuration File]----------\n\nConfiguration "))
        self.assertTrue(self.output.getvalue().endswith(
            "KrcrMZ2quIDzjn?InstanceID=not_an_instance&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("-\n\nRunning Modules:\nxennetrocket\n\n-" in self.output.getvalue())
        self.assertEqual(len(self.output.getvalue()), 1518)

        self.assertTrue(prediag_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(copyfile_mock.called)
        self.assertTrue(chdir_mock.called)
        self.assertTrue(write_config_mock.called)
        self.assertTrue(logging_fh_mock.called)
        self.assertFalse(backup_mock.called)

    @responses.activate
    @mock.patch("ec2rlcore.options.Options.write_config", side_effect=simple_return)
    @mock.patch("os.chdir", side_effect=simple_return)
    @mock.patch("shutil.copyfile", side_effect=simple_return)
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.main.Main._run_prediagnostics", side_effect=[simple_return])
    def test_main_run_zero_modules(self,
                                   prediag_mock,
                                   main_log_handler_mock,
                                   debug_log_handler_mock,
                                   mkdir_mock,
                                   copyfile_mock,
                                   chdir_mock,
                                   write_config_mock):
        """Test running the instance of Main with no modules."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_run_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_run_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._postdiags = ec2rlcore.moduledir.ModuleDir(module_path)

        # We don't want any modules for this test
        del ec2rl_run_test._prediags[:]
        del ec2rl_run_test._modules[:]
        del ec2rl_run_test._postdiags[:]

        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_run_test())
        self.assertTrue(self.output.getvalue().startswith("\n-----------[Backup  Creation]-----------\n\nNo backup op"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("-\n\nTotal modules run:               0\n\n-" in self.output.getvalue())
        self.assertEqual(len(self.output.getvalue()), 1321)
        self.assertTrue(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}.\d{6}$", self.output.getvalue(), re.M))

        self.assertTrue(prediag_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(copyfile_mock.called)
        self.assertTrue(chdir_mock.called)
        self.assertTrue(write_config_mock.called)

    @responses.activate
    @mock.patch("logging.FileHandler")
    @mock.patch("ec2rlcore.options.Options.write_config", side_effect=simple_return)
    @mock.patch("os.chdir", side_effect=simple_return)
    @mock.patch("shutil.copyfile", side_effect=simple_return)
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.main.Main._run_prediagnostics", side_effect=[simple_return])
    def test_main_run_concurrency_global_arg(self,
                                             prediag_mock,
                                             main_log_handler_mock,
                                             debug_log_handler_mock,
                                             mkdir_mock,
                                             copyfile_mock,
                                             chdir_mock,
                                             write_config_mock,
                                             logging_fh_mock):
        """Test running the instance of Main and check the length of its output to stdout."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--concurrency=1"]
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_run_test = ec2rlcore.main.Main(debug=True, full_init=True)
        ec2rl_run_test._prediags = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_run_test._postdiags = ec2rlcore.moduledir.ModuleDir(module_path)

        # We don't need to run pre/post modules for this test
        ec2rl_run_test._prediags = []
        ec2rl_run_test._postdiags = []

        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_run_test())
        self.assertTrue(self.output.getvalue().startswith("\n-----------[Backup  Creation]-----------\n\nNo backup op"))
        self.assertTrue(self.output.getvalue().endswith(
            "/SV_3KrcrMZ2quIDzjn?InstanceID=i-deadbeef&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("-\n\nRunning Modules:\nxennetrocket\n\n-" in self.output.getvalue())
        self.assertEqual(len(self.output.getvalue()), 1635)

        self.assertTrue(prediag_mock.called)
        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(copyfile_mock.called)
        self.assertTrue(chdir_mock.called)
        self.assertTrue(write_config_mock.called)
        self.assertTrue(logging_fh_mock.called)

    @mock.patch("shutil.copyfile", side_effect=OSError())
    def test_main_run_copy_error(self, mock_side_effect_function):
        """Test running the instance of Main when os.shutil fails to copy functions.bash."""
        with self.assertRaises(ec2rlcore.main.MainFileCopyError):
            self.ec2rl()
        self.assertTrue(mock_side_effect_function.called)

    @responses.activate
    def test_main_version_check_update_available(self):
        """Test that version_check returns True when there is a new version available."""
        responses.add(responses.GET, self.ec2rl.VERSION_ENDPOINT,
                      body="9999.0.0rc0", status=200)
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(self.ec2rl.version_check())
        self.assertEqual(self.output.getvalue(),
                         "Running version:  {}\nUpstream version: 9999.0.0rc0\nAn update is available.\n".format(
                             ec2rlcore.main.Main.PROGRAM_VERSION))

    @responses.activate
    def test_main_version_check_no_update_available(self):
        """Test that version_check returns False when there is no new version available."""
        responses.add(responses.GET, self.ec2rl.VERSION_ENDPOINT,
                      body="1.0.0b6", status=200)
        with contextlib.redirect_stdout(self.output):
            self.assertFalse(self.ec2rl.version_check())
        self.assertEqual(self.output.getvalue(),
                         "Running version:  {}\nUpstream version: 1.0.0b6\nNo update available.\n".format(
                             ec2rlcore.main.Main.PROGRAM_VERSION))

    @mock.patch("requests.get", side_effect=requests.exceptions.Timeout)
    def test_main_version_check_timeout(self, requests_get_mock):
        """Test that version_check raises an exception when the connection to the endpoint times out."""
        with self.assertRaises(ec2rlcore.main.MainVersionCheckTimeout):
            self.ec2rl.version_check()
            self.assertTrue(requests_get_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main_software_check_missing_software(self,
                                                  main_log_handler_mock,
                                                  debug_log_handler_mock,
                                                  mkdir_mock):
        """Test that software_check returns the expected list of software."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_softwarecheck_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/test_main_multi_run_prunemodules_fakeexecutable/")
        ec2rl_softwarecheck_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_softwarecheck_test._modules.validate_constraints_have_args(options=ec2rl_softwarecheck_test.options,
                                                                         constraint=ec2rl_softwarecheck_test.constraint,
                                                                         without_keys=["software", "distro", "sudo"])
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_softwarecheck_test.software_check())
        self.assertEqual(self.output.getvalue(),
                         "One or more software packages required to run all modules are missing.\n"
                         "Information regarding these software packages can be found at the specified URLs below.\n\n"
                         "Package-Name: test\n"
                         "Package-URL: testurl\n"
                         "Affected-Modules: arpcache\n\n")

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main_software_check_missing_software_parse_failure(self,
                                                                main_log_handler_mock,
                                                                debug_log_handler_mock,
                                                                mkdir_mock):
        """Test that software_check handles a failure to parse the package value into the name and URL."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_softwarecheck_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath,
                                   "test/modules/test_main_software_check_missing_software_parse_failure/")
        ec2rl_softwarecheck_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_softwarecheck_test._modules.validate_constraints_have_args(options=ec2rl_softwarecheck_test.options,
                                                                         constraint=ec2rl_softwarecheck_test.constraint,
                                                                         without_keys=["software", "distro", "sudo"])
        with contextlib.redirect_stdout(self.output):
            with self.assertRaises(ec2rlcore.main.MainSoftwareCheckPackageParsingFailure) as error:
                ec2rl_softwarecheck_test.software_check()
        self.assertEqual(str(error.exception),
                         "Failed to parse package string: 'unexpectedformat_https://aws.amazon.com/'. "
                         "Malformed string present in the following modules: xennetrocket")
        self.assertEqual(self.output.getvalue(),
                         "One or more software packages required to run all modules are missing.\n"
                         "Information regarding these software packages can be found at the specified URLs below.\n\n")

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("ec2rlcore.prediag.which", side_effect=[True])
    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main_main_software_check_no_missing_software(self,
                                                          main_log_handler_mock,
                                                          debug_log_handler_mock,
                                                          mkdir_mock,
                                                          which_mock):
        """Test that software_check returns the expected list of software."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_softwarecheck_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/test_main_multi_run_prunemodules_fakeexecutable/")
        ec2rl_softwarecheck_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_softwarecheck_test._modules.validate_constraints_have_args(options=ec2rl_softwarecheck_test.options,
                                                                         constraint=ec2rl_softwarecheck_test.constraint,
                                                                         without_keys=["software", "distro", "sudo"])
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_softwarecheck_test.software_check())
        self.assertEqual("All test software requirements have been met.\n", self.output.getvalue())

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
        self.assertTrue(which_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    def test_main_debug_false(self,
                              main_log_handler_mock,
                              debug_log_hander_mock,
                              mkdir_mock):
        """Test that debug handler is not called when debug=False."""
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run"]
        ec2rl_softwarecheck_test = ec2rlcore.main.Main(debug=False)
        # Avoid triggering full_init when validate_constraints_have_args is called
        ec2rl_softwarecheck_test._modules_need_init = False
        module_path = os.path.join(self.callpath, "test/modules/test_main_multi_run_prunemodules_fakeexecutable/")
        ec2rl_softwarecheck_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)
        ec2rl_softwarecheck_test._modules.validate_constraints_have_args(options=ec2rl_softwarecheck_test.options,
                                                                         constraint=ec2rl_softwarecheck_test.constraint,
                                                                         without_keys=["software", "distro", "sudo"])
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_softwarecheck_test.software_check())
        self.assertEqual(self.output.getvalue(), "One or more software packages required to run all modules are "
                                                 "missing.\nInformation regarding these software packages can be "
                                                 "found at the specified URLs below.\n\nPackage-Name: "
                                                 "test\nPackage-URL: testurl\nAffected-Modules: arpcache\n\n")
        self.assertEqual(len(self.output.getvalue()), 228)

        self.assertFalse(main_log_handler_mock.called)
        self.assertFalse(debug_log_hander_mock.called)
        self.assertFalse(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__summary_noinstance_unknown(self,
                                              main_log_handler_mock,
                                              debug_log_handler_mock,
                                              mkdir_mock):
        """
        Test that _summary() returns True and test its output when the run_status is UNKNOWN 
        and the arg --not-an-instance is given.
        """
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--not-an-instance"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)

        ec2rl_summary_test._modules[0].run_status = "UNKNOWN"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n----------[Diagnostic Results]----------\n\nmodule predi"))
        self.assertTrue(self.output.getvalue().endswith(
            "KrcrMZ2quIDzjn?InstanceID=not_an_instance&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("unknown:                     1" in self.output.getvalue())
        self.assertEqual(len(self.output.getvalue()), 1159)

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__summary_noinstance_success(self,
                                              main_log_handler_mock,
                                              debug_log_handler_mock,
                                              mkdir_mock):
        """
        Test that _summary() returns True and test its output when the run_status is SUCCESS
        and the arg --not-an-instance is given.
        """
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--not-an-instance"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)

        ec2rl_summary_test._modules[0].run_status = "SUCCESS"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n----------[Diagnostic Results]----------\n\nmodule predi"))
        self.assertTrue(self.output.getvalue().endswith(
            "KrcrMZ2quIDzjn?InstanceID=not_an_instance&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("successes:                   1" in self.output.getvalue())
        self.assertEqual(len(self.output.getvalue()), 1159)

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__summary_noinstance_failure(self,
                                              main_log_handler_mock,
                                              debug_log_handler_mock,
                                              mkdir_mock):
        """
        Test that _summary() returns True and test its output when the run_status is FAILURE
        and the arg --not-an-instance is given.
        """
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--not-an-instance"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)

        ec2rl_summary_test._modules[0].run_status = "FAILURE"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n----------[Diagnostic Results]----------\n\nmodule predi"))
        self.assertTrue(self.output.getvalue().endswith(
            "KrcrMZ2quIDzjn?InstanceID=not_an_instance&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("failures:                    1" in self.output.getvalue())
        self.assertEqual(len(self.output.getvalue()), 1159)

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)

    @mock.patch("os.mkdir", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_debug_log_handler", side_effect=simple_return)
    @mock.patch("ec2rlcore.logutil.LogUtil.set_main_log_handler", side_effect=simple_return)
    def test_main__summary_noinstance_warn(self,
                                           main_log_handler_mock,
                                           debug_log_handler_mock,
                                           mkdir_mock):
        """
        Test that _summary() returns True and test its output when the run_status is WARN
        and the arg --not-an-instance is given.
        """
        path_to_ec2rl = os.path.abspath("ec2rl")
        test_path = os.path.sep.join([os.path.split(path_to_ec2rl)[0], "test", "modules", "ec2rl"])
        sys.argv = [test_path, "run", "--not-an-instance"]
        ec2rl_summary_test = ec2rlcore.main.Main(debug=True, full_init=True)
        module_path = os.path.join(self.callpath, "test/modules/single_diagnose/")
        ec2rl_summary_test._modules = ec2rlcore.moduledir.ModuleDir(module_path)

        ec2rl_summary_test._modules[0].run_status = "WARN"
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rl_summary_test._summary())
        self.assertTrue(self.output.getvalue().startswith("\n----------[Diagnostic Results]----------\n\nmodule predi"))
        self.assertTrue(self.output.getvalue().endswith(
            "KrcrMZ2quIDzjn?InstanceID=not_an_instance&Version={}\n\n".format(ec2rlcore.main.Main.PROGRAM_VERSION)))
        self.assertTrue("warnings:                    1" in self.output.getvalue())
        self.assertEqual(len(self.output.getvalue()), 1159)

        self.assertTrue(main_log_handler_mock.called)
        self.assertTrue(debug_log_handler_mock.called)
        self.assertTrue(mkdir_mock.called)
