# udevpersistentnet module

## Problem Description
Incorrect rules in your /etc/udev/rules.d/70-persistent-net.rules file can result in interfaces not coming up with the proper interface name, or at all.

## Resolving with EC2 Rescue for Linux
EC2 Rescue for Linux will automatically comment out all lines in the rules file.
```commandline
$ sudo ./ec2rl run --only-modules=udevpersistentnet --remediate --udevpersistentnet
```

Passing output:
```commandline
----------[Diagnostic Results]----------
module run/udevpersistentnet       [SUCCESS] commented out the lines in /etc/udev/rules.d/70-persistent-net.rules
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/arpignore       [FAILURE] failed to comment out the lines in /etc/udev/rules.d/70-persistent-net.rules
```

## Resolving Manually

Move the file to a different location, delete it, or edit the file and comment out the rules.

```commandline
$ sudo mv /etc/udev/rules.d/70-persistent-net.rules /etc/udev/rules.d/70-persistent-net.bak
```
```commandline
$ sudo rm /etc/udev/rules.d/70-persistent-net.rules
```
```commandline
$ sudo vim /etc/udev/rules.d/70-persistent-net.rules
```