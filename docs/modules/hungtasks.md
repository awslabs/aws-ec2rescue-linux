# hungtasks module

## Problem Description

EC2 instances can have a 'hung task' occur. These messages are informational, and indicate that a process was blocked from running due to waiting on an IO request. These can be seen under a system that is operating more or less normally, but generally indicate an opportunity for configuration tuning, either in-instance or in your EBS/instance store setup. Sometimes they are due to problems with the storage being access. EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of hung tasks in the available system logs.  This is provided by the 'hungtasks' diagnostic module.  This module will run by default with sudo access, and can be run individually

```commandline
$ sudo ./ec2rl run --only-modules=hungtasks
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/hungtasks              [SUCCESS] No hung tasks found
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/hungtasks       [FAILURE] Hung task found
```

## Detecting Manually

Hung tasks can be detected via grepping through your messages or syslog file, depending on distribution.

```commandline
$ grep -A60 "blocked for more than" /var/log/messages
```

or

```commandline
$ grep -A60 "blocked for more than" /var/log/syslog
```

## Resolution

It is out of the scope of this module to determine the reasons a task hung waiting on IO. Common causes include:

* Underprovisioned disk. If a volume is unable to service requests quickly enough, a process can be blocked for some time waiting on an IO request.
* Misconfigured dirty page management. Too many dirty pages being flushed to disk can result in a system being unable to service other IO requests for extended periods of time.
* Storage failure. A problem with the underlying storage can prevent IO requests from being completed successfully.
