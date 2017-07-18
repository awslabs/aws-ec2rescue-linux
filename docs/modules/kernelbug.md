# kernelbug module

## Problem Description

EC2 instances can have 'kernel bugs' occur, generally due to a bug in the kernel or loaded kernel modules. These can result in panics that bring the entire system down, or otherwise cause issues with normal operation.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of kernel bugs in the available system logs.  This is provided by the 'kernelbug' diagnostic module.  This module will run by default with sudo access, and can be run individually

```commandline
$ sudo ./ec2rl run --only-modules=kernelbug
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/kernelbug              [SUCCESS] No kernel bug occurrences found
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/kernelbug       [FAILURE] No kernel bug occurrences found
```

## Detecting Manually

Kernel bugs can be detected via grepping through your messages or syslog file, depending on distribution.

```commandline
$ grep -A60 "kernel BUG at" /var/log/messages
```

or

```commandline
$ grep -A60 "kernel BUG at" /var/log/syslog
```

## Resolution

This is a general diagnostic and does not check for specific kernel bugs, so specific remediation instructions are not available. However, the best practice for resolving kernel bugs in general is to update your kernel to the latest available. If it continues after that, filing a bug report with the maintainer of the distribution is the recommended next step