# Copyright 2016-2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

"""Integration tests for Amazon Linux 2027 framework and module support."""
from __future__ import print_function

import logging
import os
import sys
import tempfile
import unittest

import ec2rlcore.main
import ec2rlcore.moduledir
import ec2rlcore.options


class _PruneOptions(object):
    """Provide the option values required by module pruning."""

    def __init__(self, domains_to_run):
        self.global_args = {"notaninstance": "False"}
        self.domains_to_run = domains_to_run
        self.classes_to_run = ["diagnose"]
        self.per_module_args = {}


class TestAL2027Support(unittest.TestCase):
    """Test AL2027 module eligibility and unsupported-platform handling."""

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def setUp(self):
        """Preserve the caller's distribution environment."""
        self.original_distro = os.environ.get("EC2RL_DISTRO")
        self.original_argv = sys.argv[:]

    def tearDown(self):
        """Restore the caller's distribution environment."""
        if self.original_distro is None:
            os.environ.pop("EC2RL_DISTRO", None)
        else:
            os.environ["EC2RL_DISTRO"] = self.original_distro
        sys.argv = self.original_argv

    def load_modules(self, relative_path):
        """Load modules from a repository-relative directory."""
        return ec2rlcore.moduledir.ModuleDir(os.path.join(self.project_root, relative_path))

    def build_pruner(self, domains_to_run):
        """Build a minimal Main instance for exercising module pruning."""
        main = object.__new__(ec2rlcore.main.Main)
        main._modules = self.load_modules("test/modules/single_diagnose")
        main._modules_need_init = False
        main.options = _PruneOptions(domains_to_run)
        main.constraint = {}
        main.pruned_modules = []
        main.prune_stats = {}
        main.logger = logging.getLogger("test_al2027_pruner")
        return main

    def test_al2027_enabled_for_validated_al2023_modules(self):
        """Every validated AL2023 module must explicitly support AL2027."""
        modules = self.load_modules("mod.d")
        al2023_modules = {
            module.name for module in modules if "al2023" in module.constraint["distro"]
        }
        al2027_modules = {
            module.name for module in modules if "al2027" in module.constraint["distro"]
        }

        self.assertEqual(len(al2023_modules), 168)
        self.assertEqual(al2027_modules, al2023_modules - {"kpatch", "rebuildinitrd"})

    def test_rebuildinitrd_and_kpatch_remain_excluded(self):
        """Unvalidated remediation and live-patching modules must remain excluded."""
        modules = self.load_modules("mod.d")

        self.assertNotIn("al2027", modules.name_map["rebuildinitrd"].constraint["distro"])
        self.assertNotIn("al2027", modules.name_map["kpatch"].constraint["distro"])

    def test_yumlog_supports_dnf5_logs_and_rotations(self):
        """The package manager log module must cover YUM/DNF5 log families."""
        yumlog = self.load_modules("mod.d").name_map["yumlog"]

        self.assertIn("al2027", yumlog.constraint["distro"])
        self.assertIn("/var/log/yum.log*", yumlog.content)
        self.assertIn("/var/log/dnf5.log*", yumlog.content)

    def test_kpatch_package_metadata_is_parseable(self):
        """Every nonempty package entry must provide a package name and URL."""
        kpatch = self.load_modules("mod.d").name_map["kpatch"]

        self.assertEqual(len(kpatch.package[0].split()), 2)

    def test_module_configuration_writes_on_python_3_14(self):
        """Module argument comments must remain writable by modern ConfigParser."""
        sys.argv = ["ec2rl", "run"]
        options = ec2rlcore.options.Options(subcommands=["run"])
        modules = self.load_modules("mod.d")

        with tempfile.NamedTemporaryFile(mode="w+") as config_file:
            options.write_config(config_file.name, modules)
            config_file.seek(0)
            generated_config = config_file.read()

        self.assertIn("# (required) period = value", generated_config)
        self.assertIn("# (optional) since = value", generated_config)

    def test_unknown_distribution_pruning_all_candidates_raises(self):
        """An unknown distribution must not produce a successful zero-module run."""
        main = self.build_pruner(["net"])
        os.environ["EC2RL_DISTRO"] = "unknown for /etc/system-release"

        with self.assertRaises(ec2rlcore.main.MainUnsupportedDistributionError):
            main._run_prunemodules()

    def test_intentional_empty_selection_remains_valid(self):
        """A filter selecting no candidate modules must remain a valid empty run."""
        main = self.build_pruner(["os"])
        os.environ["EC2RL_DISTRO"] = "unknown for /etc/system-release"

        main._run_prunemodules()

        self.assertEqual(len(main.modules), 0)
