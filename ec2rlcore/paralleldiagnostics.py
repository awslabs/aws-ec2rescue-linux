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
Parallel diagnostic module execution module.

Functions:
    parallel_run:  executes batches of modules in parallel
    _create_batches: break up the modules into batches whose contents can be executed in parallel
    _merge_batch_class: returns a set that is the union of the inputs
    _enqueue_batch: adds the given batch to the given work queue and returns the number of newly scheduled modules
    _enqueue_module: adds an individual module to the given work queue
    _start_workers: creates workers up to given concurrency
    _worker: a parallel execution thread whcih obtains work from queue

Classes:
    None

Exceptions:
    None
"""
import threading
import ec2rlcore.console_out

try:
    # noinspection PyPep8Naming
    # Python 3
    import queue as Queue
except ImportError:  # pragma: no cover
    # Python 2
    import Queue as Queue

import ec2rlcore.logutil
import ec2rlcore.module


def parallel_run(modules, logdir, options=None, concurrency=10):
    """
    Run the applicable diagnostic modules in parallel.

    Parameters:
        modules (ModuleDir): the complete "list" of modules
        logdir (str): the module log directory path
        options (Options): the complete "dict" of parsed arguments
        concurrency (int): the maximum number of threads to start to run a batch of modules

    Returns:
        (int): Count of modules run
    """
    logger = ec2rlcore.logutil.LogUtil.get_root_logger()
    logger.info("----------------------------------------")
    logger.info("BEGIN PARALLEL RUN MODULES")
    logger.info("----------------------------------------")
    logger.info("Setting up parallel execution with a concurrency of {}".format(concurrency))
    if options is None:
        logger.error("No options passed to parallel run, aborting")
        return 0
    if len(modules) <= 0:
        logger.error("No modules provided to run "
                     "or no modules able to run with the provided configuration and arguments.")
        logger.error("See the logs for more details.")
        return 0

    workers = []
    work_queue = Queue.Queue()

    _start_workers(workers, concurrency, options, work_queue, logdir)

    batches = _create_batches(modules)
    modules_scheduled = 0
    for batch in batches:
        logger.debug("Enqueueing batch {}".format(batch))
        modules_scheduled += _enqueue_batch(batch, modules, work_queue)
        logger.debug("Process queue length: {}".format(work_queue.qsize()))
        logger.info("All applicable modules queued. Waiting for completion")
        work_queue.join()

    work_queue.join()
    logger.info("All batches and work queue completed. Scheduling sentinels")
    for _ in workers:
        work_queue.put(None)
    work_queue.join()
    logger.info("Sentinels cleared, joining workers")
    for worker in workers:
        worker.join()

    logger.info("All workers completed.  Active threads: {}".
                format(threading.active_count()))
    return modules_scheduled


def _create_batches(modules):
    """
    Assigns modules into batches of modules which can run in parallel.

    Parameters:
        modules (ModuleDir): A list of applicable modules to run.
                                                 All modules will be assumed to be applicable at this stage
    Returns:
        batches (list): List of lists of modules, each batch being an element in the outer list.
    """
    logger = ec2rlcore.logutil.LogUtil.get_root_logger()
    key_to_name = dict()
    name_to_exclusives = dict()

    for module_obj in modules:
        key_to_name[modules.index(module_obj)] = module_obj.name
        name_to_exclusives[module_obj.name] = set(module_obj.constraint["parallelexclusive"])

    batches = list()
    while key_to_name:
        logger.debug("Building new batch {}, considering {} modules".format(len(batches), len(key_to_name)))
        batch = list()
        batch_exclusives = set()
        batch_class = None

        for k in key_to_name:
            name = key_to_name[k]

            if batch_class is not None and not set(modules[k].constraint["class"]) & batch_class:
                # A batch class has been selected, and this module is not in that class
                continue

            if not name_to_exclusives[name] & batch_exclusives:
                # Module exclusives are not in this batch
                # Empty sets are okay, and are the default
                batch.append(k)
                batch_exclusives = batch_exclusives.union(name_to_exclusives[name])
                batch_class = _merge_batch_class(batch_class, modules[k].constraint["class"])
                logger.debug("{} added to batch {}".format(name, len(batches)))
                logger.debug("batch {} has exclusive {} and class {}".format(
                    len(batches), batch_exclusives, batch_class))

        logger.debug("built batch, contains {} modules.  {} modules remain unclaimed".format(
            len(batch), len(key_to_name)))

        logger.debug("removing {} from remaining modules".format(batch))
        for k in batch:
            key_to_name.pop(k)
        batches.append(batch)

    return batches


def _merge_batch_class(existing, other):
    """
    Sets or unions two sets, for building batch class restrictions.
    If existing is None, the other set is returned directly

    Parameters:
        existing: iterable object of the current batch classes
        other: iterable object of batch classes to add

    Returns:
        (set): union of existing and other
    """
    if existing is None:
        return set(other)
    else:
        return set(existing).union(set(other))


def _enqueue_batch(batch, modules, work_queue):
    """
    Add a single execution batch to the work queue

    Parameters:
        batch: list of modules which are in the batch
        modules (ModuleDir): full list of modules to pick from
        work_queue (Queue): the queue of modules to be executed

    Returns:
        modules_scheduled (int): Modules added to queue in this batch
    """
    modules_scheduled = 0
    for k in batch:
        _enqueue_module(modules[k], work_queue)
        modules_scheduled += 1
    return modules_scheduled


def _enqueue_module(module_obj, work_queue):
    """
    Add a single module to the work queue

    Parameters:
        module_obj (Module): Diagnostic module to add to the work queue
        work_queue (Queue): the queue of modules to be executed

    Returns:
        True (bool)
    """
    logger = ec2rlcore.logutil.LogUtil.get_root_logger()
    logger.info("module {}/{}: Scheduling".format(module_obj.placement, module_obj.name))
    work_queue.put(module_obj)
    return True


def _start_workers(workers, concurrency, options, work_queue, logdir):
    """
    Spawn thread workers up to N concurrency.  Options are passed into the workers when starting.
    If more than concurrency workers are running, this will do nothing.  Workers will not be killed down to concurrency

    Parameters:
        workers (list): list of workers (Threads)
        concurrency: number of workers to create
        options (Options): run options for this diagnostics run
        work_queue (Queue): the queue of modules to be executed
        logdir (str): the log directory path

    Returns:
        (int): number of workers running
    """
    while len(workers) < concurrency:
        workers.append(threading.Thread(target=_worker, args=(options, work_queue, logdir)))
        workers[-1].setDaemon(True)
        workers[-1].start()
    return len(workers)


def _worker(options, work_queue, logdir):
    """
    Thread worker to run diagnostics.  Will keep picking up modules off the work queue.
    Will exit once the sentinel None is picked up off the queue

    Parameters:
        options (Options): run options for this diagnostics run
        work_queue (Queue): the queue of modules to be executed
        logdir (str): the log directory path

    Returns:
        True (bool)
    """
    logger = ec2rlcore.logutil.LogUtil.get_root_logger()
    identity = threading.current_thread().ident

    logger.debug("Worker {} started".format(identity))

    for work_item in iter(work_queue.get, None):
        try:
            logger.debug("Worker {} has module '{}'".format(identity, work_item.name))
            ec2rlcore.console_out.notify_module_running(work_item)
            module_logger = ec2rlcore.logutil.LogUtil.create_module_logger(work_item, logdir)
            module_logger.info(work_item.run(options=options))
            work_queue.task_done()
            logger.debug("Worker {} completed module '{}'".format(identity, work_item.name))
        except ec2rlcore.module.ModuleRunFailureError:
            work_queue.task_done()
            logger.debug("Worker {} failed to complete module '{}' due to a 'ModuleRunFailureError' exeception.".format(
                identity, work_item.name))
    logger.debug("Worker {} exiting".format(identity))
    work_queue.task_done()
    return True
