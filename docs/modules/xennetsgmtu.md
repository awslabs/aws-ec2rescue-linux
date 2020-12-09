# xennetsgmtu module

## Problem Description

EC2 instances utilizing paravirtual xen network drivers may see packet loss and intermittent communication problems when running on unpatched kernerls while interface MTU is set below Jumbo Frame size and Scatter Gather is disabled.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a module that examines your interface configuration for susceptibility to this bug. This is provided by the 'xennetsgmtu' module. The module will run by default with sudo access and can be run individually.

```
./ec2rl run --only-modules=xennetsgmtu
```

```
----------[Diagnostic Results]----------
module run/xennetsgmtu             [SUCCESS] Scatter-Gather is enabled on eth0. This mitigates the bug.
```

or

```
----------[Diagnostic Results]----------
module run/xennetsgmtu             [SUCCESS] MTU is set to Jumbo-Frame size on eth0. This mitigates the bug.
```

Warning output:

```
----------[Diagnostic Results]----------
module run/xennetsgmtu      [WARN] Scatter-Gather is off and MTU is set below 9001 on eth0. You are potentially susceptible to the bug.
```

## Detecting Manually

Susceptibility can be manually confirmed by checking ethtool and ifconfig configuration for the instance in question.

```
$ ethtool -k eth0 | grep "^scatter-gather: on"
  scatter-gather: on
$ ifconfig eth0 | grep "MTU:9001"
            UP BROADCAST RUNNING MULTICAST  MTU:9001  Metric:1
```
If scatter-gather is returned as "off" or the MTU is returned as 1500, the system is potentially susceptible.
Due to the kernel update that resolves the issue being delivered in a variety of versions across EC2RL support distributions, it is not within scope of this document to track known good kernels.

## Resolution

This error is best fixed by making sure you have moved to the latest kernel version provided by your distribution, or if on an instance capable of utilizing Enhanced Networking, using it rather than the paravirtual xennet driver. It can be worked around via setting MTU to 9001 for the interface on supporter instance types, or enabling scatter gather.

Workaround configuration can be done as follows:
```
$ sudo ethtool -K eth0 sg on
$ sudo ifconfig eth0 mtu 9001
```
