# ixgbevfversion module

## Problem Description

Certain older versions of the ixgbevf prior to 2.14.2 can cause network communication issues, including packet loss, link flapping, and gray failures.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will check the ixgbevf.  This is provided by the 'ixgbevfversion' diagnostic module.  This module will run by default, and can be run individually.

```commandline
$ sudo ./ec2rl run --only-modules=ixgbevfversion
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/ixgbevfversion             [SUCCESS] You are running the recommended ixgbevf driver or newer.
```

Warning output:

```commandline
----------[Diagnostic Results]----------
module run/ixgbevfversion       [WARN] You are running $VERSION which is older than $GOODVER.
```

**Note**: Intel updates the in-kernel tree driver with many of their bugfixes but does not bump the version. Not all bugfixes and changes make it into the in-kernel tree driver. This is why this defaults to warning, as it is not within the scope of this module to determine what exact fixes are present in the driver you are running.

## Detecting Manually

This can also be detected manually via greping the output of ethtool as follows

```commandline
$ ethtool -i eth0 | grep version
```

## Resolution

You will need to upgrade the ixgbevf driver. Documentation for this is available at <http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/sriov-networking.html>