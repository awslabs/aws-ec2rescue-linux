# oomkiller module

## Problem Description

EC2 instances can exhaust all available memory, causing the Linux Kernel to invoke the Out Of Memory process killer.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of the kernel's oomkiller functionality within various system logs.  This is provided by the 'oomkiller' diagnostic module.  This module will run by default with sudo access, and can be run individually

```commandline
$ sudo ./ec2rl run --only-modules=oomkiller
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/oomkiller      [SUCCESS] No oom-killer invocations found.
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/oomkiller    [FAILURE] oom-killer invocations found:
                                  (logfile output)
                              ---------------------------------------
```

## Detecting Manually

Manual detection can be accomplished by grepping the distribution-specific system logs. The logfile location will vary, depending on your specific distribution configuration.

## Resolution

This is generic diagnostic module that searches for oom-killer invocations. As each invocation can have a unique underlying cause, no specific resolution steps are available. However, it is considered best practice to investigate the application that triggered the oom-killer invocation and determine of optimizations are necessary.
