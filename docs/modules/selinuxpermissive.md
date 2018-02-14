# selinuxpermissive module

## Problem Description
SELinux being set to enforcing mode can result in systems behaving in incorrect or unexpected manners. This can be remediated by setting it to permissive mode.

## Resolving with EC2 Rescue for Linux
EC2 Rescue for Linux will automatically set the configuration to permissive mode.

```commandline
$ sudo ./ec2rl run --only-modules=selinuxpermissive --remediate --selinuxpermissive
```

Passing output:
```commandline
----------[Diagnostic Results]----------
module run/selinuxpermissive       [SUCCESS] selinux set to permissive
```

## Resolving Manually

Open /etc/selinux/config in your favorite text editor and change it to permissive mode.
```commandline
$ sudo vim /etc/selinux/config
```

Example:

```commandline
SELINUX=permissive
```