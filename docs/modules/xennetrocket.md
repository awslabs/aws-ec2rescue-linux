# xennetrocket module

## Problem Description

EC2 instances running kernels that are not up to date may see errors in their console/dmesg output with the error "xennet: skb ride the rocket: xx slots" and see packet loss and degraded network performance under certain network conditions.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a module that searches for occurrences of this error in the kernel logs. This is provided by the 'xennetrocket' module. The module will run by default with or without sudo access and can be run individually.

```
./ec2rl run --only-modules=xennetrocket
```

```
----------[Diagnostic Results]----------
module run/xennetrocket             [SUCCESS] No SKB overflow bug found
```

Failing output:

```
----------[Diagnostic Results]----------
module run/xennetrocket      [FAILURE] SKB overflow bug found. 3 occurrences in dmesg
```

## Detecting Manually

This error can be manually detected by checking the dmesg or messages/syslog output within the operating system.  The grep utility can be used to easily search the active dmesg logs to quickly identify if the error has occurred.

```
$ dmesg | grep "rides the rocket"
```

If any results are returned, then the instance has experienced the error.

## Resolution

This error is best fixed by making sure you have moved to the latest kernel version provided by your distribution, or if on an instance capable of utilizing Enhanced Networking, using it rather than the paravirtual xennet driver.
