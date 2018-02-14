# fstabfailures module

## Problem Description
An /etc/fstab that has fsck set to 1 or lacks nofail can prevent an instance from booting if a volume is misconfigured or missing, or needs a fsck.


## Resolving with EC2 Rescue for Linux

EC2 Rescue for Linux will automatically disable fsck and enable nofail for your volumes, or write a sane default fstab if it is missing.

```commandline
$ sudo ./ec2rl run --only-modules=fstabfailures --remediate --fstabfailures
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/fstabfailure       [SUCCESS] /etc/fstab rewritten
```

## Resolving Manually

Open your /etc/fstab with your preferred text editor
```commandline
$ sudo vim /etc/fstab
```

Make sure that all volume mount points have nofail in the options list and the fsck (sixth) column set to 0.

Example:
```commandline
LABEL=/     /           ext4    defaults,noatime,nofail  0   0
```

