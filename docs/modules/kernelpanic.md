# kernelpanic module

## Problem Description

EC2 instances can have 'kernel panics' occur for a variety of reasons, including kernel bugs, hardware issues with the underlying host, issues with storage, and other problems.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of kernel panics in the available system logs.  This is provided by the 'kernelpanic' diagnostic module.  This module will run by default with sudo access, and can be run individually

```commandline
$ sudo ./ec2rl run --only-modules=kernelpanic
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/kernelpanic              [SUCCESS] No kernel panic occurrences found
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/kernelpanic       [FAILURE] Kernel panic occurrences found
```

## Detecting Manually

Kernel panic can be detected via grepping through your messages or syslog file, depending on distribution.

```commandline
$ grep -A60 "kernel panic" /var/log/messages
```

or

```commandline
$ grep -A60 "kernel panic" /var/log/syslog
```

## Resolution

This is a general diagnostic and does not check for specific kernel panics, so specific remediation instructions are not available. However, the best practices for resolving kernel panics include updating your kernel to the latest available, performing a stop and start to rule out hardware issues, and investigating the stack trace in depth to determine what actually occurred.