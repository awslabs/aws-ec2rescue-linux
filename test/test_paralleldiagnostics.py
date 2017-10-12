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

"""Unit tests for "paralleldiagnostics" module."""
import os
import sys
import unittest
import time
import threading

try:
    # Python 3.x
    import queue as Queue
except ImportError:  # pragma: no cover
    # Python 2.7
    import Queue as Queue

try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

import mock

import ec2rlcore.console_out
import ec2rlcore.logutil
import ec2rlcore.module
import ec2rlcore.moduledir
import ec2rlcore.options
import ec2rlcore.paralleldiagnostics

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib


def simple_return(*args, **kwargs):
    return True


class TestParallelDiagnostics(unittest.TestCase):
    """Testing class for "paralleldiagnostics" unit tests."""
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

    logdir = os.path.join(callpath, "test")

    def tearDown(self):
        sys.argv = self.argv_backup
        # Reset the global variable that tracks the first module execution
        ec2rlcore.console_out._first_module = True
        self.output.close()

    def setUp(self):

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
        sys.argv = ["ec2rl"]
        self.options = ec2rlcore.options.Options(subcommands=["run"])

        self.work_queue = Queue.Queue()
        self.workers = []
        self.output = StringIO()

    def load_modules_from_list(self, modules_to_load):
        """
        Helper to build a list of Module objects from a list of names

        Parameters:
            modules_to_load: list(str) list of module names to load

        Returns:
            list(Module): list of Modules
        """
        modules = list()
        for module_name in modules_to_load:
            module_obj = ec2rlcore.module.get_module(os.path.join(self.callpath, "test/modules/mod.d", module_name))
            modules.append(module_obj)
        return modules

    def generic_batch_test(self, modules_to_load, expected_batches):
        """
        Performs a generic batch test given a list of module names and expected batch layout

        Parameters:
            modules_to_load: list(str) List of modules to test by name
            expected_batches: list(list(int), ...) List of Lists of int describing the batch layout
                    batch each int in the batch layout is the key of the module in modules_to_load
        """
        modules = self.load_modules_from_list(modules_to_load)
        batches = ec2rlcore.paralleldiagnostics._create_batches(modules)
        self.assertListEqual(batches, expected_batches)

    def test_paralleldiagnostics_helper_load_modules_from_list_elements(self):
        """
        Self-tests if the load_modules_from_list helper function works.
        Checks if two modules are loaded given two module names
        """
        modules_to_load = ["aptlog.yaml", "arpcache.yaml"]
        modules = self.load_modules_from_list(modules_to_load)
        self.assertEqual(len(modules), 2)

    def test_paralleldiagnostics_helper_load_modules_from_list_type(self):
        """
        Self-tests if the load_modules_from_list helper function works.
        Checks if modules are of the ec2rlcore.module.Module type
        """
        modules_to_load = ["aptlog.yaml", "arpcache.yaml"]
        modules = self.load_modules_from_list(modules_to_load)
        self.assertIsInstance(modules[0], ec2rlcore.module.Module)

    def test_paralleldiagnostics_create_batches_same_class_with_exclusives(self):
        """Test ec2rlcore.paralleldiagnostics._create_batch with a set of 3 exclusive modules."""
        self.generic_batch_test(["bccbiolatency.yaml", "bccbiosnoop.yaml", "bccbiotop.yaml"],
                                [[0], [1], [2]])

    def test_paralleldiagnostics_create_batches_same_class_without_exclusives(self):
        """Test ec2rlcore.paralleldiagnostics._create_batch with a set of 3 non-exclusive modules."""
        self.generic_batch_test(["arptable.yaml", "arptablesrules.yaml", "dig.yaml"],
                                [[0, 1, 2]])

    def test_paralleldiagnostics_create_batches_three_class_without_exclusives(self):
        """Test ec2rlcore.paralleldiagnostics._create_batch with a set of 4 modules containing 3 classes."""
        self.generic_batch_test(["aptlog.yaml", "arptablesrules.yaml", "arpcache.yaml", "arptable.yaml"],
                                [[0], [1, 3], [2]])

    def test_paralleldiagnostics_create_batches_three_class_with_exclusives(self):
        """
        Test ec2rlcore.paralleldiagnostics._create_batch with a set of 6 modules containing 3 classes and exclusives.
        """
        self.generic_batch_test(["aptlog.yaml", "arptablesrules.yaml", "arpcache.yaml",
                                 "arptable.yaml", "bccbiolatency.yaml", "bccbiosnoop.yaml"],
                                [[0], [1, 3, 4], [2], [5]])

    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("logging.FileHandler")
    def test_paralleldiagnostics_worker_runs_module(self, logging_fh_mock, os_makedirs_mock):
        """Test ec2rlcore.paralleldiagnostics._worker if it runs a module and exits on the None sentinel."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        modules = self.load_modules_from_list(["ex.yaml"])
        self.work_queue.put(modules[0])
        self.work_queue.put(None)
        with contextlib.redirect_stdout(self.output):
            ec2rlcore.paralleldiagnostics._worker(self.options, self.work_queue, self.logdir)
        self.assertEqual(self.output.getvalue(), "Running Modules:\nex")
        self.assertGreater(len(modules[0].processoutput), 5)
        self.assertIn("module 'ex'", modules[0].processoutput)
        self.assertTrue(logging_fh_mock.called)
        self.assertTrue(os_makedirs_mock.called)

    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("logging.FileHandler")
    def test_paralleldiagnostics_worker_runs_module_with_failure(self, logging_fh_mock, os_makedirs_mock):
        """Test that a module failure is caught and handled."""
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        module_obj = ec2rlcore.module.get_module(os.path.join(self.callpath, "test/modules/bad_mod.d/ex_fails.yaml"))
        self.work_queue.put(module_obj)
        self.work_queue.put(None)
        with contextlib.redirect_stdout(self.output):
            ec2rlcore.paralleldiagnostics._worker(self.options, self.work_queue, self.logdir)
        self.assertEqual(self.output.getvalue(), "Running Modules:\nex")
        self.assertEqual("module 'ex' can write a message to the main output\n", module_obj.processoutput)
        self.assertTrue(logging_fh_mock.called)
        self.assertTrue(os_makedirs_mock.called)

    def test_paralleldiagnostics_start_workers_makes_workers(self):
        """Test ec2rlcore.paralleldiagnostics._start_workers if correct number of workers."""
        ec2rlcore.paralleldiagnostics._start_workers(self.workers, 2, self.options, self.work_queue, self.logdir)
        self.assertEqual(len(self.workers), 2)

        # Clean up workers
        # This is tested in test_workers_lifecycle_sentinels()
        for _ in self.workers:
            self.work_queue.put(None)

    def test_paralleldiagnostics_start_workers_doesnt_start_above_concurrency_limit(self):
        begin_threads = threading.active_count()
        ec2rlcore.paralleldiagnostics._start_workers(self.workers, 2, self.options, self.work_queue, self.logdir)
        self.assertEqual(len(self.workers), 2)

        ec2rlcore.paralleldiagnostics._start_workers(self.workers, 2, self.options, self.work_queue, self.logdir)
        self.assertEqual(len(self.workers), 2)

        ec2rlcore.paralleldiagnostics._start_workers(self.workers, 1, self.options, self.work_queue, self.logdir)
        self.assertEqual(len(self.workers), 2)

        # Clean up workers
        # This is tested in test_workers_lifecycle_sentinels()
        for _ in self.workers:
            self.work_queue.put(None)

    def test_paralleldiagnostics_start_workers_does_start_additional_workers(self):
        begin_threads = threading.active_count()
        ec2rlcore.paralleldiagnostics._start_workers(self.workers, 2, self.options, self.work_queue, self.logdir)
        # Must have more threads than we started with, and 2 workers
        self.assertGreater(threading.active_count(), begin_threads)
        self.assertEqual(len(self.workers), 2)

        ec2rlcore.paralleldiagnostics._start_workers(self.workers, 4, self.options, self.work_queue, self.logdir)
        # Must have 4 workers
        self.assertEqual(len(self.workers), 4)

        # Clean up workers
        # This is tested in test_workers_lifecycle_sentinels()
        for _ in self.workers:
            self.work_queue.put(None)

    def test_paralleldiagnostics_workers_lifecycle_sentinels(self):
        sys.argv = ["ec2rl"]
        options = ec2rlcore.options.Options(subcommands=["run"])
        work_queue = Queue.Queue()
        workers = []
        ec2rlcore.paralleldiagnostics._start_workers(workers, 2, options, work_queue, self.logdir)
        for worker in workers:
            self.assertTrue(worker.is_alive(), "Worker not alive")

        for _ in workers:
            work_queue.put(None)
        work_queue.join()
        # Short wait for workers to return after receiving signaling work complete.
        time.sleep(0.2)
        for worker in workers:
            self.assertFalse(worker.is_alive(), "Worker is still alive")

    def test_paralleldiagnostics_enqueue_module(self):
        modules = self.load_modules_from_list(["ex.yaml", "dig.yaml"])
        ec2rlcore.paralleldiagnostics._enqueue_module(modules[0], self.work_queue)
        self.assertEqual(self.work_queue.qsize(), 1)
        self.assertEqual(self.work_queue.get(), modules[0])

    def test_paralleldiagnostics_enqueue_batch(self):
        batch = [0, 1, 3]
        modules = self.load_modules_from_list(["ex.yaml", "dig.yaml", "arptable.yaml", "dmesg.yaml"])
        ec2rlcore.paralleldiagnostics._enqueue_batch(batch, modules, self.work_queue)
        for i in batch:
            work_item = self.work_queue.get()
            self.assertEqual(work_item, modules[i])
            self.work_queue.task_done()

    @mock.patch("os.makedirs", side_effect=simple_return)
    @mock.patch("logging.FileHandler")
    @mock.patch("ec2rlcore.module.Module.run", return_value="NotRunning")
    def test_paralleldiagnostics_parallel_run_module_count(self, run_mock, logging_fh_mock, os_makedirs_mock):
        logging_fh_mock.setFormatter = mock.MagicMock(return_value=True)
        modules = self.load_modules_from_list(["aptlog.yaml", "arptablesrules.yaml", "arpcache.yaml",
                                               "arptable.yaml", "bccbiolatency.yaml", "bccbiosnoop.yaml"])
        with contextlib.redirect_stdout(self.output):
            modules_scheduled = ec2rlcore.paralleldiagnostics.parallel_run(modules, self.logdir, self.options, 2)
        self.assertEqual(self.output.getvalue(),
                         "Running Modules:\naptlog, arptablesrules, arptable, bccbiolatency, arpcache, bccbiosnoop")
        self.assertEqual(len(self.output.getvalue()), 87)
        self.assertEqual(modules_scheduled, 6)
        self.assertTrue(run_mock.called)
        self.assertTrue(logging_fh_mock.called)
        self.assertTrue(os_makedirs_mock.called)

    def test_paralleldiagnostics_parallel_run_exits_on_missing_options(self):
        ec2rlcore.logutil.LogUtil.disable_console_output()
        modules = self.load_modules_from_list(["aptlog.yaml", "arptablesrules.yaml", "arpcache.yaml",
                                               "arptable.yaml", "bccbiolatency.yaml", "bccbiosnoop.yaml"])
        modules_scheduled = ec2rlcore.paralleldiagnostics.parallel_run(modules, self.logdir, None, 2)
        self.assertEqual(modules_scheduled, 0)

    def test_paralleldiagnostics_parallel_run_exits_on_empty_modules(self):
        ec2rlcore.logutil.LogUtil.disable_console_output()
        modules = self.load_modules_from_list([])
        modules_scheduled = ec2rlcore.paralleldiagnostics.parallel_run(modules, self.logdir, self.options, 2)
        self.assertEqual(modules_scheduled, 0)
