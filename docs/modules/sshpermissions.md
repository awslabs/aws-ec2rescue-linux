# sshpermissions module

## Problem Description

SSH Key Pair based login utilizes the authorized_keys file containing permitted public keys.  The authorized_keys file permissions cannot have write permissions for group or other users, otherwise the SSH daemon will disallow this file.

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will check the file permissions of authorized_keys for all users with home folders.  This is provided by the 'sshpermissions' diagnostic module.  This module will run by default, and can be run individually. This module requires sudo access.

```commandline
$ sudo ./ec2rl run --only-modules=sshpermissions
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/sshpermissions        [SUCCESS] Permissions are valid for SSH.
```

Warning output:

```commandline
----------[Diagnostic Results]----------
module run/sshpermissions        [WARN] one or more of the tested users missing /home/<user>/.ssh/authorized_keys
```
**Note**: This warning indicates  a user found in the /home directory does not have an authorized_keys file, and therefore cannot use SSH keypair authentication.  You will need to add this file to the user if they intend to log in via SSH keypair authentication.

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/sshpermissions        [FAILURE] Permissions for authorized_keys or a parent directory for one or more of the tested users are too permissive.
```

## Detecting Manually

This can also be detected manually via examining each user's authorized_keys file.

```commandline
$ ls -la /home/ec2-user/.ssh/authorized_keys
-rw-rw-rw- 1 ec2-user   ec2-user   0 Jul 11 14:00 authorized_keys
```

When checking each users' authorized_keys file, you will need to check that there are not write permissions on group or other.  You may need to use sudo to view files and directories owned by a different user.

You will need to do the same for the user's home directory and .ssh directory.

```commandline
$ ls -la /home/ | grep ec2-user
drwxrw-rw- 15 ec2-user ec2-user 4096 Jul  7 14:00 ec2-user

$ ls -la /home/ec2-user | grep .ssh
drwxrw-rw-  2 ec2-user ec2-user    4096 Jun 28 19:11 .ssh

```



## Resolution

You will need to remove the write permissions to group and other with chmod.  You may need to use sudo to modify files owned by a different user.
```commandline
$ chmod go-rw /home/ec2-user/.ssh/authorized_keys
$ chmod go-rw /home/ec2-user/.ssh
$ chmod go-rw /home/ec2-user
```