# udevpersistentnet module

## Problem Description
Incorrect rules in your /etc/udev/rules.d/70-persistent-net.rules file can result in interfaces not coming up with the proper interface name, or at all.

## Resolving with EC2 Rescue for Linux
EC2 Rescue for Linux will automatically move the rules to a backed up location, which will result in proper rules being generated upon reboot.

```commandline
$ sudo ./ec2rl run --only-modules=udevpersistentnet --remediate --udevpersistentnet
```

Passing output:
```commandline
----------[Diagnostic Results]----------
module run/udevpersistentnet       [SUCCESS] Moved /etc/udev/rules.d/70-persistent-net.rules to /etc/udev/rules.d/70-persistent-net.bak
```

## Resolving Manually

Move the file to a different location or delete it.

```commandline
$ sudo mv /etc/udev/rules.d/70-persistent-net.rules /etc/udev/rules.d/70-persistent-net.bak
```