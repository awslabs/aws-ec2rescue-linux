# duplicatefsuuid module

## Problem Description

EC2 instances allow for multiple volumes to be attached to them at any given point. Each filesystem within those volumes will be assigned a UUID for unique identification.  Duplicate filesystem UUIDs can cause undesired issues.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of duplicate UUIDs in the mounted filesystems.  This is provided by the 'duplicatefsuuid' diagnostic module.  This module will run by default with sudo access, and can be run individually

```commandline
$ sudo ./ec2rl run --only-modules=duplicatefsuuid
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/duplicatefsuuid           [SUCCESS] No duplicate filesystem UUIDs found.
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/duplicatefsuuid    [FAILURE] Duplicate UUID, {UUID}, found on the following filesystems: {UUID} {Block Device ID(s)}
```

## Detecting Manually

Duplicate UUIDs can be found by manually iterating over each filesystem within the EC2 Instance.

Fetch current filesystem UUID from /dev/xvdX, where X is your block device identifier (a, b, c, etc.)

```commandline
$ blkid -s UUID /dev/xvdX
```

A sample output:

```commandline
/dev/xvda1: UUID="{UUID}"
```

Note the output, and compare against the results of any other filesystems within the EC2 instance.

## Resolution

Resolution can involve one of two options. The first is to change the UUID on one of the volumes. The second is to detach the volume from the affected EC2 instance.

### Changing the UUID.

Care should be taken to ensure that /etc/fstab is updated after the volume filesystem UUID is adjusted. Failure to do so can cause the EC2 instance to not boot, and other production-impacting issues.

A sample command to change the filesystem UUID. You can generate the new UUID randomly, or based on time.

```commandline
$ sudo tune2fs /dev/{device} -U {random/time}
```
