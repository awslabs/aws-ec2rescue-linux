# duplicatelabels module

## Problem Description

EC2 instances allow for multiple volumes to be attached to them at any given point. Each filesystem within those volumes can be assigned a label to make system administration tasks easier.  Duplicate filesystem labels can cause undesired issues.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of duplicate labels in the mounted filesystems.  This is provided by the 'duplicatelabels' diagnostic module.  This module will run by default with sudo access, and can be run individually

```commandline
$ sudo ./ec2rl run --only-modules=duplicatelabels
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/duplicatelabels           [SUCCESS] No duplicate filesystem labels found.
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/duplicatelabels    [FAILURE] Duplicate label, {LABEL}, found on the following filesystems: {LABEL} {Block Device ID(s)}
```

## Detecting Manually

Duplicate labels can be found by manually iterating over each filesystem within the EC2 Instance.

Fetch current filesystem label from /dev/xvdX, where X is your block device identifier (a, b, c, etc.)

```commandline
$ blkid -s LABEL /dev/xvdX
```

A sample output:

```commandline
/dev/xvda1: LABEL="/"
```

Note the output, and compare against the results of any other filesystems within the EC2 instance.

## Resolution

Resolution can involve one of two options. The first is to change the label on one of the volumes. The second is to detach the volume from the affected EC2 instance.

### Changing the label.

Care should be taken to ensure that /etc/fstab is updated after the volume filesystem label is adjusted. Failure to do so can cause the EC2 instance to not boot, and other production-impacting issues.

A sample command to change the filesystem label.
```commandline
$ sudo tune2fs -L (NEW LABEL) /dev/xvdX
```
