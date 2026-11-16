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

import six

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
    """Test AL2027 module eligibility and compatibility."""

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

        self.assertEqual(
            al2027_modules,
            al2023_modules - {"fstabfailures", "kpatch", "rebuildinitrd"},
        )

    def test_unvalidated_or_incompatible_modules_remain_excluded(self):
        """Unvalidated remediation and live-patching modules must remain excluded."""
        modules = self.load_modules("mod.d")

        self.assertNotIn("al2027", modules.name_map["fstabfailures"].constraint["distro"])
        self.assertNotIn("al2027", modules.name_map["rebuildinitrd"].constraint["distro"])
        self.assertNotIn("al2027", modules.name_map["kpatch"].constraint["distro"])

    def test_enadiag_version_comparison_uses_supported_standard_library(self):
        """The ENA version check must run without the removed distutils package."""
        enadiag = self.load_modules("mod.d").name_map["enadiag"]
        namespace = {"__name__": "test_enadiag"}

        self.assertNotIn("distutils", enadiag.content)
        six.exec_(enadiag.content, namespace)

        namespace["get_ena_version"] = lambda: "2.2.11g"
        self.assertTrue(namespace["compare_ena_version"]())
        namespace["get_ena_version"] = lambda: "2.2.9g"
        self.assertFalse(namespace["compare_ena_version"]())

    def test_yumlog_supports_dnf5_logs_and_rotations(self):
        """The package manager log module must safely cover YUM and DNF logs."""
        yumlog = self.load_modules("mod.d").name_map["yumlog"]

        self.assertIn("al2027", yumlog.constraint["distro"])
        self.assertIn("/var/log/yum.log*", yumlog.content)
        self.assertIn("/var/log/dnf.log*", yumlog.content)
        self.assertIn("/var/log/dnf.rpm.log*", yumlog.content)
        self.assertIn("/var/log/dnf5.log*", yumlog.content)
        self.assertIn("-f ${log_file}", yumlog.content)
        self.assertIn("! -L ${log_file}", yumlog.content)
        self.assertNotIn("|| true", yumlog.content)
        self.assertIn("may contain credentials", yumlog.helptext)

    def test_yumconfiguration_supports_dnf5(self):
        """The package manager configuration module must use DNF5 paths and syntax."""
        yumconfiguration = self.load_modules("mod.d").name_map["yumconfiguration"]

        self.assertIn("/etc/dnf/dnf.conf", yumconfiguration.content)
        self.assertIn("yum repo list --all", yumconfiguration.content)

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

    def test_unknown_distribution_pruning_all_candidates_remains_valid(self):
        """Unknown distributions must retain the established zero-module behavior."""
        main = self.build_pruner(["net"])
        os.environ["EC2RL_DISTRO"] = "unknown for /etc/system-release"

        main._run_prunemodules()

        self.assertEqual(len(main.modules), 0)
