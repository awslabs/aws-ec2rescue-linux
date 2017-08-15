# tcprecycle module

## Problem Description

TCP Connection recycling may cause networking issues when source TCP connections originate from a NAT device.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will check the status of TCP Connection Recycling. This is provided by the 'tcprecycle' diagnostic module.  This module will run by default with sudo access, and can be run individually

```commandline
$ sudo ./ec2rl run --only-modules=tcprecycle
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/tcprecycle            [SUCCESS] Aggressive TCP recycling is disabled."
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/tcprecycle       [FAILURE] You have aggressive TCP connection recycling enabled. This may cause networking issues when source TCP connections originate from a NAT device.
```

## Detecting Manually

Kernel panic can be detected through checking the net.ipv4.tcp_tw_recycle kernel option. No output indicates that the TCP Connection Recycling setting is disabled.

```commandline
sysctl net.ipv4.tcp_tw_recycle |grep "= 1"
```

## Resolution

This setting can be disabled on a temporary or permanent basis.

To disable it temporarily:

```commandline
sudo sysctl -w net.ipv4.tcp_tw_recycle=0
```

To disable it permanently

```commandline
echo 'net.ipv4.tcp_tw_recycle=0' | sudo tee /etc/sysctl.conf
```
