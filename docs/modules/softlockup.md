# softlockup module

## Problem Description

EC2 instances can have CPU 'soft lockups' occur. These messages are informational, and indicate that a CPU did not respond to a softlockup timer within the timer window, indicating a CPU heavy load. In some cases, it can also be caused by a program not relinquishing a spinlock in a timely manner. EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of soft lockups in the available system logs.  This is provided by the 'softlockup' diagnostic module.  This module will run by default with sudo access, and can be run individually

## Detecting with EC2 Rescue for Linux

```commandline
$ sudo ./ec2rl run --only-modules=softlockup
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/softlockup              [SUCCESS] No CPU soft lockup occurrences found
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/softlockup       [FAILURE] Soft lockup occurrence found
```

## Detecting Manually

CPU soft lockups can be detected via grepping through your messages or syslog file, depending on distribution.

```commandline
$ grep -A60 "soft lockup" /var/log/messages
```

or

```commandline
$ grep -A60 "soft lockup" /var/log/syslog
```

## Resolution

These are informational messages and as such generally do not need to be specifically remediated, and generally indicate a system is under a CPU intense workload. If the system is operating normally, these can likely be ignored. If it is experiencing performance issues, they point to being CPU bound on the current instance. If the workload is not CPU bound and they are recurring, it can be indicative of a program not relinquishing their spinlocks, which could be due to a software bug or other problems and should be investigated in more depth.
