# arpignore module

## Problem Description

Arpignore being set on an interface can cause networking to experience issues and instance health checks to fail.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will check the arp ignore setting.  This is provided by the 'arpignore' diagnostic module.  This module will run by default, and can be run individually.

```commandline
$ sudo ./ec2rl run --only-modules=arpignore
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/arpignore             [SUCCESS] arp ignore is disabled for all interfaces.
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/arpignore       FAILURE] arp ignore is enabled for one or more interfaces. Please see the module log
```

## Detecting Manually

This can also be detected manually via grepping the output of sysctl as follows

```commandline
$ /sbin/sysctl net.ipv4.conf | grep 'arp_ignore'
```

## Resolving with EC2 Rescue for Linux

```commandline
$ sudo ./ec2rl run --only-modules=arpcache --remediate
```

Passing output:
```commandline
----------[Diagnostic Results]----------
module run/arpignore       [SUCCESS] arp ignore is disabled for all interfaces after remediation." 
```

## Resolving Manually

Several commands are needed to resolve the issue.

The first will disable it for the current run. Replace the # with the interface number it is disabled on

```commandline
$ sudo sysctl -w net.ipv4.conf.eth#.arp_ignore=0"
```

The next will make it persistant across reboots

```commandline
echo "net.ipv4.conf.eth#.arp_ignore = 0" | sudo tee /etc/sysctl.d/55-arp-ignore.conf
```
