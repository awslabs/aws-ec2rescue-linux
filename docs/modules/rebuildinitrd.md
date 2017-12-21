# rebuildinitrd module

## Problem Description
A corrupted or improperly built initial ramdisk an prevent an instance from booting.

## Resolving with EC2 Rescue for Linux
EC2 Rescue for Linux will automatically rebuild your initial ramdisk.

```commandline
$ sudo ./ec2rl run --only-modules=rebuildinitrd --remediate --rebuildinitrd
```

Passing output:
```commandline
----------[Diagnostic Results]----------
module run/rebuildinitrd       [SUCCESS] initial ramdisk rebuilt
```

## Resolving Manually
Rebuilding your initial ramdisk will vary from system to system.

You will need to modify the command to specify a kernel version that is available on your system in /boot

Amazon Linux AMI:
```commandline
dracut -f /boot/initramfs-KERNELVERSION.img
```

Ubuntu:
```commandline
update-initramfs -c -k KERNELVERSION
```

RHEL:
```commandline
dracut -f /boot/initramfs-KERNELVERSION.img
```

SUSE:
```commandline
dracut -f /boot/initrd-KERNELVERSION
```
