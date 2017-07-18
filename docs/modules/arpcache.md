# arpcache module

## Problem Description

Certain kernel versions have changed the default behavior for clearing arp caches. In environments where IPs are likely to be re-used, such as EC2 when using autoscaling, this can cause communication failure due to the cached MAC adress being incorrect.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will check the arp caching setting.  This is provided by the 'arpcache' diagnostic module.  This module will run by default, and can be run individually.

```commandline
$ sudo ./ec2rl run --only-modules=arpcache
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/arpcache             [SUCCESS] Aggressive arp caching is disabled.
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/arpcache       [FAILURE] You have aggressive arp caching enabled.
```

## Detecting Manually

This can also be detected manually via greping the output of sysctl as follows

```commandline
$ /sbin/sysctl net.ipv4.neigh.default | grep 'thresh1'
```

## Resolution

Several commands are needed to resolve the issue.

The first will disable it for the current run

```commandline
$ sudo sysctl -w net.ipv4.neigh.default.gc_thresh1=0'
```

The next will make it persistant across reboots

```commandline
echo 'net.ipv4.neigh.default.gc_thresh1 = 0' | sudo tee /etc/sysctl.d/55-arp-gc_thresh1.conf
```
