[![Gitter chat](https://badges.gitter.im/gitterHQ/gitter.png)](https://gitter.im/aws-ec2rescue-linux/Lobby) [![Build Status](https://travis-ci.org/awslabs/aws-ec2rescue-linux.svg?branch=develop)](https://travis-ci.org/awslabs/aws-ec2rescue-linux)
# Amazon Elastic Compute Cloud (EC2) Rescue for Linux

## What is it?
Amazon Elastic Compute Cloud (EC2) Rescue for Linux (ec2rl) is a framework for executing diagnostic and
troubleshooting modules to analyze and remediate issues on Linux instances on AWS.

## The Latest Version
### Builds
Two builds of the latest version are provided:
1. The standard build only includes the EC2 Rescue for Linux code and requires the system meet the [Prerequisites](#prerequisites).
2. The bundled build includes a minimal copy of Python. It is intended for use on systems that do not meet the Python version prerequisite. Please see the [FAQ](#what-are-the-limitations-of-the-bundled-build) for limitations associated with this build.
### Downloads
| Build | Download | sha256 hash | GPG signature |
|:---:|:---:|:---:|:---:|
| Standard | [Link](https://s3.amazonaws.com/ec2rescuelinux/ec2rl.tgz) | [Link](https://s3.amazonaws.com/ec2rescuelinux/ec2rl.tgz.sha256) | [Link](https://s3.amazonaws.com/ec2rescuelinux/ec2rl.tgz.sig) |
| Bundled | [Link](https://s3.amazonaws.com/ec2rescuelinux/ec2rl-bundled.tgz) | [Link](https://s3.amazonaws.com/ec2rescuelinux/ec2rl-bundled.tgz.sha256) | [Link](https://s3.amazonaws.com/ec2rescuelinux/ec2rl-bundled.tgz.sig) |

Our GPG public key can be downloaded from [here](https://s3.amazonaws.com/ec2rescuelinux/ec2rl.key).

### Integrity Verification
File integrity can be verified in two ways. The examples below demonstrate verifying the standard build.

#### sha256 hash
Example:
```commandline
[ec2-user@localhost ~]$ wget -q https://s3.amazonaws.com/ec2rescuelinux/ec2rl.tgz.sha256
[ec2-user@localhost ~]$ sha256sum -c ec2rl.tgz.sha256
ec2rl.tgz: OK
```

#### Detached GPG signature with GPG public key
Example:
```commandline
[ec2-user@localhost ~]$ wget -q https://s3.amazonaws.com/ec2rescuelinux/ec2rl.tgz.sig
[ec2-user@localhost ~]$ wget -q https://s3.amazonaws.com/ec2rescuelinux/ec2rl.key
[ec2-user@localhost ~]$ gpg2 --import ec2rl.key
[ec2-user@localhost ~]$ gpg2 --verify ec2rl.tgz.sig
...
gpg: Good signature from "ec2autodiag@amazon.com <EC2 Rescue for Linux>"
...
```

## Documentation
Available in docs/ subdirectory

## Prerequisites
Python 2.7.9+ / 3.2+

## Installation
No ec2rl specific installation required. Unpack the tarball and run the tool.

## Usage
```
ec2rl:  A framework for executing diagnostic and troubleshooting
        modules for analyzing issues on Linux instances on AWS.

USAGE:
    ec2rl [subcommand] [parameters]

COMMANDS:
  The following are the accepted subcommands:
    menu-config    - use a text-based menu system to create a configuration file, configuration.cfg
    save-config    - use the provided arguments to create a configuration file, configuration.cfg
    run            - executes modules
    list           - list available modules for platform
    upload         - upload a tarball of a directory to S3 using either a presigned URL or an AWS-support provided URL
    help           - print long help
    version        - print version and license information
    version-check  - check program version against the latest upstream version
    software-check - check for software required by modules that is not installed on the system and give install details
    bug-report     - print version information relevant for inclusion in a bug report
```

Additional usage information is available in the usage guide in docs/USAGE.md and the help subcommand output.

## Examples

ec2rl can be run with no options or special configuration.
```commandline
ec2rl run
```

Some modules require sudo/root. Utilizing sudo is required in order to run these modules if executing ec2rl as a regular user.
```commandline
sudo ec2rl run
```

Some modules require arguments for their usage. For example, most performance metric collection modules require times (number of samples to take) and period (length of sample).

```commandline
sudo ec2rl run --times=3 --period=5
```

Some modules may negatively impact system performance. These modules require the perfimpact argument to run.

```commandline
sudo ec2rl run --times=3 --period=5 --perfimpact=true
```

Some modules detect an issue and can also remediate the issue. These modules require the remediate argument to perform the remediation actions.

```commandline
sudo ec2rl run --remediate
```

## Module Development
Modules are YAML files containing either a BASH or a Python script as well as the necessary metadata. Examples are available in mod.d and the module development guide found in docs/MODULE.md

## FAQ
### Why does EC2 Rescue For Linux not have the ability to run and upload in a single command?
It is recommended the resulting data be reviewed prior to being uploaded in order to ensure that no confidential information is included.

### Why does EC2 Rescue For Linux require Python 2.7.9+? What about Python 2.7.x, x < 9?
SSL SNI (Server Name Indication) is required for the ec2rl's upload functionality, however, this wasn't added to Python 2.7 until 2.7.9. See [PEP 466](https://www.python.org/dev/peps/pep-0466/) for more information regarding the SSL changes in Python 2.7.9.

### What are the limitations of the bundled build?
SSL and curses functionality may not work depending upon the versions of these libraries on the system. This impacts three subcommands:
1. The "menu-config" subcommand may not function.
2. The "upload" subcommand may not function.
3. The "version-check" subcommand may not function.

### I'm trying to use the menu on a system running SUSE, but it does not work.
Python's curses module is normally built into its standard library, however, it is sometimes separated and included as a separate package. You will need to install it with the operating system's package manager. The package name in SUSE Linux Enterprise Server 12 is "[python-curses](https://www.suse.com/LinuxPackages/packageRouter.jsp?product=server&version=12&service_pack=&architecture=x86_64&package_name=python-curses)".

## Licensing
Please see the file called LICENSE.
