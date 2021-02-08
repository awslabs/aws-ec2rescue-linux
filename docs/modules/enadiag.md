# enadiag module

## Problem Description

Versions of the Elastic Network Adapter driver 2.2.10 include additional statistics around queueing or throttling of packets based on instance network limits.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will check the ena statistics for each device.  This is provided by the 'enadiag' diagnostic module.  This module will run by default, and can be run individually.

```commandline
$ sudo ./ec2rl run --only-modules=enadiag
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/enadiag               [SUCCESS] No ENA problems found on eth0.
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/enadiag               [FAILURE] ENA problems found on eth0.
                                     472 bw_in_allowance_exceeded events found.
                                     173 pps_allowance_exceeded events found.
                                 Please visit https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/troubleshooting-ena.html for more details on stat counters.
```


## Detecting Manually

This can also be detected manually via checking the stats via ethtool as below: 

```commandline
$ ethtool -S eth0
```

## Resolution

There are variety of stats checked. You can see https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/troubleshooting-ena.html for details on each stat.
Resolving the issue will depend on the details found.
