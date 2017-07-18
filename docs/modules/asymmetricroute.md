# asymmetricroute module

## Problem Description

When utilizing multiple interfaces on a server, if proper route tables are not created, you could potentially be sending all traffic over a single interface, even when the request came in on the other interface. This can result in performance bottlenecks, or complete lack of communications succeeding.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will check your network configuration to determine if you have multiple interfaces configured in a way that will result in asymmetric routing. This is provided by the 'asymmetricroute' module. It will be run by default, and can be run individually.

```commandline
$ sudo ./ec2rl run --only-modules=asymmetricroute
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/asymmetricroute           [SUCCESS] No duplicate subnets found.

OR

----------[Diagnostic Results]----------
module run/asymmetricroute           [SUCCESS] Routing for additional interfaces is configured correctly.  All interfaces have a matching route rule

OR

----------[Diagnostic Results]----------
module run/asymmetricroute           [SUCCESS] Routing for additional interfaces is configured correctly.  Only one interface will use the default rule.
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/asymmetricroute           [FAILURE] Potential asymmetric routing problems detected.  More than one interface has an un-matched routing rule" 

```

## Detecting Manually

There isn't a single command that can be used to detect this issue manually, but instead several things that will need to be done.

First, you will want to confirm that you have multiple interfaces on the same network. This can be done with the 'ip addr show' command.

```cmdline

$ ip addr show
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9001 qdisc mq state UP group default qlen 1000
    link/ether 0a:9e:69:90:7d:cc brd ff:ff:ff:ff:ff:ff
    inet 172.16.1.128/24 brd 172.16.1.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::89e:69ff:fe90:7dcc/64 scope link
       valid_lft forever preferred_lft forever
3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9001 qdisc mq state UP group default qlen 1000
    link/ether 0a:9e:69:90:7d:dd brd ff:ff:ff:ff:ff:ff
    inet 172.16.1.16/24 brd 172.16.1.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::89e:69ff:fe90:7dcc/64 scope link
       valid_lft forever preferred_lft forever

```

The easiest thing to look for is the line with 'inet' and the address and 'brd' fields - if you se multiple hthings with the same 'brd', or broadcast address, you know that you have multiple interfaces on the same network. This means you are suspecptible to asymmetric routing.

Next we will need to determine if they have a routing rule/table setup for them. We'll be using 'ip rule show' and 'ip route show table all' for this.

```cmdline
$ ip rule show | grep 172.16
32765:	from 172.16.1.16 lookup 10001


$ ip route show table all | grep 172.16
default via 172.16.1.1 dev eth1  table 10001
172.16.1.0/24 dev eth1  table 10001  proto kernel  scope link  src 172.16.1.16
default via 172.16.1.1 dev eth0
default via 172.16.1.1 dev eth1  metric 10001
172.16.1.0/24 dev eth0  proto kernel  scope link  src 172.16.1.128
172.16.1.0/24 dev eth1  proto kernel  scope link  src 172.16.1.16
broadcast 172.16.1.0 dev eth0  table local  proto kernel  scope link  src 172.16.1.128
broadcast 172.16.1.0 dev eth1  table local  proto kernel  scope link  src 172.16.1.16
local 172.16.1.16 dev eth1  table local  proto kernel  scope host  src 172.16.1.16
local 172.16.1.128 dev eth0  table local  proto kernel  scope host  src 172.16.1.128
broadcast 172.16.1.255 dev eth0  table local  proto kernel  scope link  src 172.16.1.128
broadcast 172.16.1.255 dev eth1  table local  proto kernel  scope link  src 172.16.1.16
```

From these outputs you can see that there are additional rules and routing tables setup to handle the second interface. If these are not there, you will need to add them.

## Resolution

The easiest way to resolve this is to simply utilize two route tables. This will mean that traffic that comes in on one interface will return traffic via the same interface. Further tuning can be done with setting rules and policy, but that is beyond the scope of this document.

```cmdline
$ ip route add default via 192.168.16.1 dev eth0 tab 1
$ ip route add default via 192.168.16.1 dev eth1 tab 2


$ ip route show table 1
default via 192.168.16.1 dev eth0

$ ip route show table 2
default via 192.168.16.1 dev eth1

```