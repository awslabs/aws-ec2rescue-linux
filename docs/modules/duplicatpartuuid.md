# duplicatepartuuid module

## Problem Description

EC2 instances allow for multiple volumes to be attached to them at any given point. Each partition within those volumes will be assigned a UUID for unique identification.  Duplicate partition UUIDs can cause undesired issues.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of duplicate UUIDs in the mounted partitions.  This is provided by the 'duplicatepartuuid' diagnostic module.  This module will run by default with sudo access, and can be run individually

```commandline
$ sudo ./ec2rl run --only-modules=duplicatepartuuid
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/duplicatepartuuid           [SUCCESS] No duplicate partition UUIDs found.
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/duplicatepartuuid    [FAILURE] Duplicate UUID, {UUID}, found on the following partitions: {UUID} {Block Device ID(s)}
```

## Detecting Manually

Duplicate UUIDs can be found by manually iterating over each partition within the EC2 Instance.

Fetch current partition UUID from /dev/xvdX, where X is your block device identifier (a, b, c, etc.)

```commandline
$ blkid -s PARTUUID /dev/xvdX
```

A sample output:

```commandline
/dev/xvda1: PARTUUID="{UUID}"
```

Note the output, and compare against the results of any other partitions within the EC2 instance.

## Resolution

Resolution can involve one of two options. The first is to change the UUID on one of the volumes. The second is to detach the volume from the affected EC2 instance.

### Changing the UUID

Care should be taken to ensure that /etc/fstab is updated after the volume partition UUID is adjusted. Failure to do so can cause the EC2 instance to not boot, and other production-impacting issues.

A sample command to change the partition UUID.

```commandline
$ sudo gdisk /dev/xvdX
GPT fdisk (gdisk) version 0.8.10

Partition table scan:
  MBR: protective
  BSD: not present
  APM: not present
  GPT: present

Found valid GPT with protective MBR; using GPT.
-
# x to enter Expert mode
Command (? for help): x
-
# c to change partition UUID
Expert command (? for help): c
-
# partition number you want to change
Partition number (1-128): 1
-
# R to randomly generate a new UUID
Enter the partition's new unique GUID ('R' to randomize): R
-
New GUID is D63B44EC-D7C4-45FA-992A-0A7147B9B7A4
-
# w to write the changes
Expert command (? for help): w
-
Final checks complete. About to write GPT data. THIS WILL OVERWRITE EXISTING
PARTITIONS!!
-
# Y to save changes
Do you want to proceed? (Y/N): Y
-
OK; writing new GUID partition table (GPT) to /dev/xvda.
Warning: The kernel is still using the old partition table.
The new table will be used at the next reboot.
The operation has completed successfully.
```
