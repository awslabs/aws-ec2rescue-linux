# openssh module

## Problem Description
OpenSSH public key based authenication requires a valid server-side configuration file, a minimum set of configuration options, and correctly configured permission modes and ownership of various files such as keys, configuration files, and their parent directories. If any one of these are improperly configured, the OpenSSH daemon may fail to start and/or be unable to authenticate users.

## Detecting with EC2 Rescue for Linux

### Overview
The "openssh" module for EC2 Rescue for Linux is a diagnostic module that checks for and corrects many problems that prevent the OpenSSH daemon from starting and/or authenticating a user. This module does not require any arguments to run, but it does requires sudo access since the remediation actions interact with files only readable and/or writable by the root user. The module performs the following checks:

1.  Utilize sshd's test mode to verify the following:
    1. Existence of the server configuration file.
    2. Validity of the keyword-argument pairs in the server configuration file.
    3. Existence of the privilege separation directory.
    4. Presence of host keys, if supported (see "Known Limitations").
    5. Existence of the privilege separation user.
2.  Presence of duplicate AuthorizedKeysFile keyword-argument pairs in sshd configuration file.
3.  Existence of, file mode, and owner of the relative AuthorizedKeysFile paths for each user.
4.  Existence of, file mode, and owner of the absolute AuthorizedKeysFile paths.
6.  File mode and owner of the privilege separation directory.
7.  File mode and owner of /etc/ssh and its contents.
8.  File mode and owner of any host keys defined in the server configuration that have not been previously checked during the prior steps.
9.  If remediation is enabled, remediation of problems discovered during these checks.

This module can also be used to inject new OpenSSH public keys into users' authorized keys files. This action can be performed standalone or as a precursor to the standard checks that are performed. This module supports using the key from the Instance Metadata Service, a user-specified key, and generating a new RSA key pair. See the parameters for additional details.

### Parameters

The OpenSSH module can utilize several parameters from EC2 Rescue For Linux.

1. --remediate

Enable remediation of detected problems. Also required for key injection functionality.

2. --inject-key

Inject a new public key into the authorized_keys file for each user whose home directory is in /home. The default behavior is to obtain the key from the metadata of the running instance. Alternatively, the key can be specified via the new-ssh-key parameter or a new key pair can be generated with --create-new-keys. This action is performed prior to any problem checking and before any other remediation steps. The inject-key parameter is dependent upon the --remediate parameter.

3. --inject-key-only

As with --inject-key, but when this parameter is given, the remainder of the module functionality is skipped. Use this parameter to perform key injection as a standalone action.

4. --new-ssh-key="new key value"

Specify the value of the new public key for use with the inject-key parameter. This is useful when using the module in a system that is not an instance or when a particular public key is required, but is not available from the instance metadata. This parameter always takes precendence over --create-new-keys.

5. --create-new-keys

Generate a new 4096-bit RSA key pair using ssh-keygen. The public key will be injected as previously described and the private key will be securely stored using AWS Systems Manager Parameter Store for later retrieval. This parameter only functions within an AWS EC2 instance and requires that the AWS credentials have sufficient permissions to use the SSM put_parameter API call.

### Example
```
[ec2-user@localhost ~]$ sudo ./ec2rl run --only-modules=openssh --remediate --inject-key --new-key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDQwbc5itEVp5PqNyp/xkhdyYpXbzUEo0m2w1n49rkymJ7aSLUiaGIvvOqxRYkplfvGesxS90V5lo47O2bEw6y/iEvzy2wUHWCywlGw6klPwbdzfNrV8kk0uOI/rY6e+rJoOQBO2Asut3vDz3bj6hdJ/4NLsQYyFKv+vnEDzWzRAhO3KLa7JhlEvCg4O1WBgC4ko4b8OswI3cjrpRt3NgxC9W81qdSxE44YCUVb2JGm14VJvyiWDDMz4u7RRCvsefCAZxRt7W3UADVm9PiUJA80vrIXirx1ShQYGIu61hz0nLtR/NGPWdweJOKt4PERJ1Ht7b99BL8NsXyO3wS6lr7j documentation-example-key"
```

Passing output

```
----------[Diagnostic Results]----------
module run/openssh        [SUCCESS] All configuration checks passed or all detected problems fixed.
```

Warning output

```
----------[Diagnostic Results]----------
module run/openssh        [WARN] Unable to fully validate one or more OpenSSH components.
```

Failing output when run without remediation:

```
----------[Diagnostic Results]----------
module run/openssh        [FAILURE] Improper configuration of one or more OpenSSH components.
```
Failing output when run with remediation:

```
----------[Diagnostic Results]----------
module run/openssh        [FAILURE] Failed to remediate one or more problems.
```

## Detecting Manually

### Utilize sshd's test mode to verify the following:

Validating the server configuration is performed using sshd's test mode. It is necessary to run sshd's test mode either as a user with sudo or as root in order to validate the host keys and privilege separate directory as these must not be readable or writable by any user other than root. The order presented below is also the order in which each item is verified by OpenSSH.

#### Existence of the server configuration file.

The location of the OpenSSH daemon configuration file is often /etc/ssh/sshd_config. With two levels of debug verbosity turned on, the test mode will print the configuration file path. Additionally, if the file is missing, a message indicating this will be printed.

The example below shows the result of sshd failing to find the server configuration file.

```
[ec2-user@localhost ~]$ sudo sshd -t -dd
debug2: load_server_config: filename /etc/ssh/sshd_config
/etc/ssh/sshd_config: No such file or directory
```

#### Validity of the keyword-argument pairs in the server configuration file.

An incorrect keyword-argument pair in the configuration file will result in the printing of an error message describing the problem. 

The example below shows shows the result of sshd finding an invalid option followed by the use of awk to check the offending line of the configuration file. Upon inspection, it is apparent that the port argument of "A" needs to be corrected.

```
[ec2-user@localhost ~]$ sudo sshd -t
/etc/ssh/sshd_config line 19: Badly formatted port number.
[ec2-user@localhost ~]$ awk '{ if (NR==19) print $0 }' /etc/ssh/sshd_config 
Port A
```

#### Existence of the privilege separation directory.

Privilege separation is an option enabled by default in OpenSSH. The privilege separation directory is where the unprivileged child process performs the network processing portion of the authentication process.

The below example shows the result of sshd failing to find the privilege escalation directory.

```
[ec2-user@localhost ~]$ sudo sshd -t
Missing privilege separation directory: /var/empty/sshd
```

#### Presence of host keys.

**Important note** Versions of OpenSSH that have been patched to support GSSAPI may not support this check. Since Kerberos-based authentication does not require host keys, the patch removes the check from sshd's test mode.

When performing key-based authentication, the a host key pair is used to encrypt (private key) and decrypt (public key) authentication messages.

The example below shows the result of sshd failing to find a host key.

```
[ec2-user@localhost ~]$ sudo sshd -t
Could not load host key: /etc/ssh/ssh_host_rsa_key
Could not load host key: /etc/ssh/ssh_host_ecdsa_key
Could not load host key: /etc/ssh/ssh_host_ed25519_key
sshd: no hostkeys available -- exiting.
```

#### Existence of the privilege separation user.

Privilege separation is an option enabled by default in OpenSSH. A privilege separation user is required to create an unprivileged child process to perform the network processing portion of the authentication process.

The example below shows example result of sshd failing to find the privilege separation user.

```
[ec2-user@localhost ~]$ sudo sshd -t
Privilege separation user sshd does not exist
```

### Presence of duplicate AuthorizedKeysFile keyword-argument pairs in sshd configuration file.

Multiple AuthorizedKeysFile keyword-argument pairs in the server configuration file do not cause an explicit failure, however, only the first is line is used when the configuration file is parsed.

The example below shows a second AuthorizedKeysFile line which would be ignored by OpenSSH.

```
[ec2-user@localhost ~]$ grep AuthorizedKeysFile /etc/ssh/sshd_config
AuthorizedKeysFile .ssh/authorized_keys
AuthorizedKeysFile .anotherdir/.ssh/authorized_keys
```

### Existence of, file mode, and owner of the AuthorizedKeysFile paths.

This includes both relative paths for each user and absolute paths. Each component of the path needs to be checked starting with the user's home directory. These directories and file must exist and must not be writable by group or other. This module assumes that any absolute paths must be owned by the root user.

The example below shows a failing configuration. Both directories and the authorized_keys file are writable by group and other.

```
[ec2-user@localhost ~]$ ls -ld /home/ec2-user/
drwxrwxrwx 8 ec2-user ec2-user 4096 Sep 10 21:55 /home/ec2-user/
[ec2-user@localhost ~]$ ls -ld /home/ec2-user/.ssh/
drwxrwxrwx 2 ec2-user ec2-user 4096 Aug 28 21:59 /home/ec2-user/.ssh/
[ec2-user@localhost ~]$ ls -l /home/ec2-user/.ssh/authorized_keys
drwxrwxrwx 1 ec2-user ec2-user 403 Aug 14 18:57 /home/ec2-user/.ssh/authorized_keys
```

### File mode and owner of the privilege separation directory.

The privilege separation directory must be owned by and only writable by root.

The example below shows a failing configuration. The directory is writable by group and other.

```
[ec2-user@localhost ~]$ sudo ls -ld /var/empty/sshd
drwxrwxrwx 2 root root 4096 Sep  6 00:17 /var/empty/sshd
[ec2-user@localhost ~]$ sudo sshd -t
/var/empty/sshd must be owned by root and not group or world-writable.
```

### File mode and owner of /etc/ssh and its contents.

The /etc/ssh directory and the files contained within must only be writable by root. Additionally, the private keys (file names ending in "_key") must only be readable by root.

The example below shows a configuration that meets the file mode and ownership requirements.

**NOTE:** In some distribuions, these keys are instead group readable for the ssh_keys group. This is due to a packaging change with the openssh module.

```
[ec2-user@localhost ~]$ ls -ld /etc/ssh/
drwxr-xr-x 4 root root 4096 Sep 10 22:47 /etc/ssh/
[ec2-user@localhost ~]$ ls -l /etc/ssh
total 280
-rw-r--r-- 1 root root 242153 Mar 22 00:08 moduli
-rw-r--r-- 1 root root   2278 Mar 22 00:08 ssh_config
-rw-r--r-- 1 root root   4096 Aug 31 20:44 sshd_config
-rw------- 1 root root    668 Aug 14 18:57 ssh_host_dsa_key
-rw-r--r-- 1 root root    611 Aug 14 18:57 ssh_host_dsa_key.pub
-rw------- 1 root root    227 Aug 14 18:57 ssh_host_ecdsa_key
-rw-r--r-- 1 root root    183 Aug 14 18:57 ssh_host_ecdsa_key.pub
-rw------- 1 root root    387 Aug 14 18:58 ssh_host_ed25519_key
-rw-r--r-- 1 root root     82 Aug 14 18:58 ssh_host_ed25519_key.pub
-rw------- 1 root root   1679 Aug 14 18:57 ssh_host_rsa_key
-rw-r--r-- 1 root root    403 Aug 14 18:57 ssh_host_rsa_key.pub
```

### File mode and owner of any host keys defined in the server configuration that have not been previously checked.

A system's OpenSSH host keys often reside in the /etc/ssh directory, but OpenSSH can be configured to use host keys located elsewhere. Verify whether any additional host key paths have been defined in the configuration file. If so, verify the permission mode and owner of these host key files.

The example below shows several host key paths defined in the configuration file.

```
[ec2-user@localhost ~]$ grep HostKey /etc/ssh/sshd_config
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
```

## Manual Resolution

Below are manual methods of resolving the problems detected by this module.

### Existence of the server configuration file.

A missing server configuration file can be recreated with the distribution's package manager. Below are examples for the four supported Linux distributions.

Amazon Linux
```
[ec2-user@localhost ~]$ sudo yum reinstall openssh-server
```

Ubuntu
```
[ec2-user@localhost ~]$ sudo apt-get install --reinstall openssh-server
or
[ec2-user@localhost ~]$ sudo dpkg-reconfigure openssh-server
```

Red Hat
```
[ec2-user@localhost ~]$ sudo yum reinstall openssh-server
```

SUSE
```
[ec2-user@localhost ~]$ sudo zypper --force install openssh
```

### Validity of the keyword-argument pairs in the server configuration file.

Correct or remove the improperly configured options.

### Existence of the privilege separation directory.

Create the privilege separation directory and set the permission mode.

```
[ec2-user@localhost ~]$ sudo mkdir -p /var/empty/sshd
[ec2-user@localhost ~]$ sudo chmod 0711 /var/empty/sshd
```

### Presence of host keys.

Use ssh-keygen to create a set of host keys.

```
[ec2-user@localhost ~]$ sudo ssh-keygen -q -t dsa -f /etc/ssh/ssh_host_dsa_key -N "" -C ""
[ec2-user@localhost ~]$ sudo sssh-keygen -q -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key -N "" -C ""
[ec2-user@localhost ~]$ sudo sssh-keygen -q -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N "" -C ""
[ec2-user@localhost ~]$ sudo sssh-keygen -q -t rsa -f /etc/ssh/ssh_host_rsa_key -N "" -C ""
```

### Existence of the privilege separation user.

Create the user. Create the user's home directory if it does not already exist. Set the permission mode for the user's home directory.

```
[ec2-user@localhost ~]$ sudo useradd sshd -s /sbin/nologin -c "Privilege-separated SSH" -d /var/empty/sshd
[ec2-user@localhost ~]$ sudo mkdir /var/empty/sshd
[ec2-user@localhost ~]$ sudo chmod 0711 /var/empty/sshd
```

### Existence of, file mode, and owner of AuthorizedKeysFile paths.

Use mkdir to create missing directories. If needed, adjust ownership and the file mode with chown and chmod.

```
[ec2-user@localhost ~]$ mkdir /home/testuser
[ec2-user@localhost ~]$ chmod go-rw /home/testuser
[ec2-user@localhost ~]$ chown testuser:testuser /home/testuser
```

Use chmod to remove the write permission for group and other.  It may be necessary to use sudo to modify files owned by another user.

```
[ec2-user@localhost ~]$ chmod go-rw /home/ec2-user
[ec2-user@localhost ~]$ chmod go-rw /home/ec2-user/.ssh
[ec2-user@localhost ~]$ chmod go-rw /home/ec2-user/.ssh/authorized_keys
```

### File mode and owner of the privilege separation directory.

Change the owner of the directory to root and set the permission mode.

```
[ec2-user@localhost ~]$ sudo chown root:root /var/empty/sshd
[ec2-user@localhost ~]$ sudo chmod 0711 /var/empty/sshd
```

### File mode and owner of /etc/ssh and its contents.

Change ownership of /etc/ssh and its contents to root. Make /etc/ssh writable only by root. Set the group and other permission for all files contained within to read only then remove the group and other permissions from the private keys.

**NOTE:** In some distribuions, these keys hould instead be group readable for the ssh_keys group. This is due to a packaging change with the openssh module. 
```
[ec2-user@localhost ~]$ sudo chown -R root:root /etc/ssh
[ec2-user@localhost ~]$ sudo chmod go-w /etc/ssh
[ec2-user@localhost ~]$ GLOBIGNORE="*_key"
[ec2-user@localhost ~]$ sudo chmod -R go=r /etc/ssh/*
[ec2-user@localhost ~]$ unset GLOBIGNORE
[ec2-user@localhost ~]$ sudo chmod go-rwx /etc/ssh/ssh_host_{dsa,ecdsa,ed25519,rsa}_key
[ec2-user@localhost ~]$ ls -ld /etc/ssh/
drwxr-xr-x 4 root root 4096 Sep 10 22:47 /etc/ssh/
[ec2-user@localhost ~]$ ls -l /etc/ssh
total 280
-rw-r--r-- 1 root root 242153 Mar 22 00:08 moduli
-rw-r--r-- 1 root root   2278 Mar 22 00:08 ssh_config
-rw-r--r-- 1 root root   4096 Aug 31 20:44 sshd_config
-rw------- 1 root root    668 Aug 14 18:57 ssh_host_dsa_key
-rw-r--r-- 1 root root    611 Aug 14 18:57 ssh_host_dsa_key.pub
-rw------- 1 root root    227 Aug 14 18:57 ssh_host_ecdsa_key
-rw-r--r-- 1 root root    183 Aug 14 18:57 ssh_host_ecdsa_key.pub
-rw------- 1 root root    387 Aug 14 18:58 ssh_host_ed25519_key
-rw-r--r-- 1 root root     82 Aug 14 18:58 ssh_host_ed25519_key.pub
-rw------- 1 root root   1679 Aug 14 18:57 ssh_host_rsa_key
-rw-r--r-- 1 root root    403 Aug 14 18:57 ssh_host_rsa_key.pub
```

### File mode and owner of any host keys defined in the server configuration that have not been previously checked during the prior steps.

Change ownership of the key pairs to root. Set the group and other permission for all these key files to read only on the public keys then remove all group and other permissions from the private keys.

```
[ec2-user@localhost ~]$ grep HostKey /etc/ssh/sshd_config
HostKey /etc/ssh/other_keys/ssh_host_rsa_key
HostKey /etc/ssh/other_keys/ssh_host_ecdsa_key
HostKey /etc/ssh/other_keys/ssh_host_ed25519_key
[ec2-user@localhost ~]$ sudo chown root:root /etc/ssh/other_keys/ssh_host_{dsa,ecdsa,ed25519,rsa}_key*
[ec2-user@localhost ~]$ sudo chmod go=r /etc/ssh/other_keys/ssh_host_{dsa,ecdsa,ed25519,rsa}_key.pub
[ec2-user@localhost ~]$ sudo chmod go-rwx /etc/ssh/other_keys/ssh_host_{dsa,ecdsa,ed25519,rsa}_key
```

## Known Limitations
1. Only key-based authentication is supported. Alternate authentication methods, such as passwords and Kerberos, are beyond the scope of this module.
2. Only the global section is supported. Keyword-argument pairs in match sections are handled the same as if they were in the global section.
3. Only users whose home directories are in /home are supported.
4. Versions of OpenSSH that have been patched to support GSSAPI may not support verification of the presence of host keys.
5. OpenSSH token usage in the configuration file, such as %h to refer to the user's home directory, is unsupported. The following example line would be ignored due to the inclusion of the "%u" token:
    1. AuthorizedKeysFile /var/ssh/%u/auth_keys
