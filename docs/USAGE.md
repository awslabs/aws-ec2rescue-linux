# EC2RL Usage Guide
## Using the 'help' subcommand
You can familiarize yourself with EC2 Rescue For Linux by exploring its functionality using the 'help' subcommand.
For example:
```
 ./ec2rl help
ec2rl:  A framework for executing diagnostic and troubleshooting
        modules for analyzing issues onf Linux instances on AWS.

USAGE:
    ec2rl [subcommand] [parameters]

COMMANDS:
The following are the accepted subcommands:
    menu-config   - use a text-based menu system to create a configuration file, configuration.cfg
    save-config   - use the provided arguments to create a configuration file, configuration.cfg
    run           - executes modules
    list          - list available modules for platform
    upload        - upload a tarball of a directory to S3 using either a presigned URL or an AWS-support provided URL
    help          - print long help

<.....>

SPECIAL:
    A small number of options that have special meaning to the ec2rl framework
    and are not passed to modules.

    OPTIONS:
        --config-file=filename     - loads a configuration file containing module-specific and global-module options
        --pdb                      - run framework inside the Python Debugger
```

The help subcommand can be run for any module or subcommand. For example:

```
./ec2rl help run
./ec2rl help tcpdump
```

## Run a Module
First determine which modules you wish to run. The 'list' subcommand provides a list of modules that can be run:

```
./ec2rl list

Here is a list of available modules that apply to the current host:

  Module Name         Class     Domain       Description
* aptlog              gather    os           Collect apt log files
  arpcache            diagnose  net          Determines if aggressive arp caching is enabled
  arptable            collect   net          Collect output from ip neighbor show for system analysis
 
  <....>
  
To see module  help, you can run:

ec2rl help [MODULEa ... MODULEx]
ec2rl help [--only-modules=MODULEa ... MODULEx] [--only-domains=DOMAINa ... DOMAINx]
```

For this scenario, we will use the 'ncport' module.
The 'help' subcommand can be used to display a module's required and optional parameters:

```
./ec2rl help ncport
ncport:
Test network connectivity to a specific TCP port on a network destination.
Assumes that the port is listening
Requires --destination= for destination IP or hostname/FQDN
Requires --port= for destination port
Requires sudo: False
```

When running this module the destination address and port are required. Below is an example of running this module with these parameters.

**Note**: By default, EC2 Rescue For Linux will run as many modules as possible given the operating system configuration and provided parameters.
This behavior can be changed to run a specific set of modules by adding --only-modules=comma,delimited,modulenames after the 'run' subcommand.

Beyond just --only-modules=, you can also use --only-classes= and --only-domains=. If using several of these together, the modules that run will be an intersection of the modules/classes/domains specified. (For example, specifying a class of diagnose and a module of vmstat would result in no modules running.)

```
./ec2rl run --only-modules=ncport --destination=amazon.com --port=80
----------[Configuration File]----------

Configuration file saved:
/var/tmp/ec2rl/2017-07-13T18_57_02.072742/configuration.cfg

-------------[Output  Logs]-------------

The output logs are located in:
/var/tmp/ec2rl/2017-07-13T18_57_02.072742

--------------[Module Run]--------------

Running Modules:
ncport

--------------[Run  Stats]--------------

Total modules run:               1
'collect' modules run:           1

----------------[NOTICE]----------------

Please note, this directory could contain sensitive data depending on modules run! Please review its contents!

----------------[Upload]----------------

You can upload results to AWS Support with the following, or run 'help upload' for details on using an S3 presigned URL:

./ec2rl upload --upload-directory=/var/tmp/ec2rl/2017-07-13T18_57_02.072742 --support-url="URLProvidedByAWSSupport" 

The quotation marks are required, and if you ran the tool with sudo, you will also need to upload with sudo.

---------------[Feedback]---------------

We appreciate your feedback. If you have any to give, please visit:
https://aws.au1.qualtrics.com/jfe1/form/SV_3KrcrMZ2quIDzjn?InstanceID=i-025fcbead6ab951d6&Version=1.0.0
```

The output includes the log directory, '/var/tmp/ec2rl/2017-07-13T18_57_02.072742/'.
Individual module logs are stored in '<log directory>/mod_out/<placement>/<module name>.log'.
The 'ncport' belongs to the 'run' placement. A module's placement group determines when it is run.
For more information on the different module placements, please see the Module Development Guide.
Using this information, the log can be located and inspected:

```
cat /var/tmp/ec2rl/2017-07-13T18_57_02.072742/mod_out/run/ncport.log 
I will test a TCP connection from this ubuntu box, to amazon.com on port 80
Connection to amazon.com 80 port [tcp/http] succeeded!
```
**Note**: Some modules require root access! These will require running EC2 Rescue For Linux as root or via sudo.

##Upload the Results

The upload subcommand provides a method of uploading the results directory to S3.
There are two main options for doing so: the first requires an S3 presigned URL, and the other requires a URL provided by AWS Premium Support.
The syntax for both options is as follows:

```
./ec2rl upload --upload-directory=path --presigned-url=url
./ec2rl upload --upload-directory=path --support-url=url
```

A full example:

```
./ec2rl upload --upload-directory=/var/tmp/ec2rl/2017-07-13T18_57_02.072742/ --support-url="https://aws-support-uploader.s3.amazonaws.com/uploader?account-id=832671032136&case-id=2019161061&expiration=1489442306&key=474a0f381176db0e291fc1819b48a153b93b0225c4c6ba1447fb088c5192e7b6"

Upload successful
```

**Note**: The URL must be enclosed inside double quotes!
**Note**: If you ran EC2 Rescue For Linux using sudo then sudo is also needed to read the files output from that execution of EC2 Rescue For Linux in order to upload them!

## Creating Backups
EC2 Rescue For Linux provides a backup method that runs prior to any modules.
If the instance has IAM role that supports it, you can create an automatic backup.
This includes AMIs as well as volume specific snapshots.

```
./ec2rl run --backup=ami

-----------[Backup  Creation]-----------

Creating AMI ami-04c51a12 for i-025fcbead6ab951d6

<...>
```

Or all volumes:

```
./ec2rl run --backup=allvolumes

-----------[Backup  Creation]-----------

Creating snapshot snap-0be8c6601b470fdd4 for volume vol-04739f1f82f7666d5
```

Or by volume id:

```
./ec2rl run --backup=vol-04739f1f82f7666d5

-----------[Backup  Creation]-----------

Creating snapshot snap-0059785cf2abd66c5 for volume vol-04739f1f82f7666d5
```

# Classes and Domains

## Class
Class specifies the type of action the module performs. There are three different module classes.

### Diagnose
Diagnostic module with hard pass/fail requirements. Will provide a SUCCESS, WARNING, or FAILURE.
The output will get stored in the mod_out/run directory.

### Collect
Diagnostic module that collects information from the output of a command. 
The output will get stored in the mod_out/run directory

### Gather
Diagnostic module that gathers files from the local machine.
The output will get stored in the mod_out/gathered_out directory

## Domain
Domain specifies the scope of the task the module performs. There are four different module domains.
### Application
Application modules perform tasks related to a specific application such as Apache or NGINX.

### Net
Net modules perform tasks related to networking such as collecting interface information and performing connectivity testing.

### OS
OS modules perform tasks related to the operating system itself such as collecting configuration files and inspecting filesystems.

### Performance
Performance modules perform tasks related to performance such as collecting CPU and memory metrics.
