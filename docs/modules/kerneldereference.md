# kerneldereference module

## Problem Description

EC2 instances can have 'kernel null pointer dereferences' occur, generally due to a bug in the kernel or loaded kernel modules. These can result in panics that bring the entire system down, or otherwise cause issues with normal operation.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of kernel null pointer dereferences in the available system logs.  This is provided by the 'kerneldereference' diagnostic module.  This module will run by default with sudo access, and can be run individually

```
$ sudo ./ec2rl run --only-modules=kerneldereference
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/kerneldereference              [SUCCESS] No kernel null pointer dereference occurrences found
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/kerneldereference       [FAILURE] No kernel null pointer dereference occurrences found
```

## Detecting Manually

Kernel null pointer dereferences can be detected via grepping through your messages or syslog file, depending on distribution.

```commandline
$ grep -A60 "kernel NULL pointer dereference" /var/log/messages
```

or

```commandline
$ grep -A60 "kernel NULL pointer dereference" /var/log/syslog
```

## Resolution

This is a general diagnostic and does not check for specific kernel null pointer dereferences, so specific remediation instructions are not available. However, the best practice for resolving kernel null pointer dereferences in general is to treat them as a kernel bug and update your kernel to the latest available. If it continues after that, filing a bug report with the maintainer of the distribution is the recommended next step.