# Module Development Guide
## Module Structure
### Overview
Modules are written in YAML, a data serialization standard. A module's YAML file consists of a single document, representing the module and its attributes.
### Module Attributes
#### name
The name of the module. The name should be <= 18 characters in length.
#### version
The version number of the module.
#### title
Short title/description of module. This value should be <= 50 characters in length.
#### helptext
 The extended description of the module. Each line of this value should be <= 75 characters in length. If the module consumes arguments, required or optional, include them in the helptext value. For example:
```
helptext: !!str |
  Collect output from ps for system analysis
  Consumes --times= for number of times to repeat
  Consumes --period= for time period between repetition
```
#### placement
The stage in which the module should be run. Valid values include "prediagnostic", "run", and "postdiagnostic".
#### language
The language in which the module code is written. BASH and Python are supported. Python code must be compatible with both Python 2.7.9+ and Python 3.2+.
#### content
The entirety of the script code.
#### constraint
The name of the object containing the constraint values.
#### domain
A descriptor of how the module is grouped/classified. The set of included modules uses the domains "application", "net", "os", and "performance".
#### class
A descriptor of the type of task performed by the module. The set of included modules uses the classes "collect" (collects output from programs), "diagnose" (pass/fail based on a set of criteria), and "gather" (copies files and writes to specific file).
#### distro
The list of Linux distributions this module supports. The set of included modules use the distributions "alami" (Amazon Linux), "rhel", "ubuntu", and "suse"
#### required
The required arguments the test is consuming from the CLI options.
#### optional
The optional arguments that the test can utilize.
#### software
The software executables used in of the test. This attribute is intended to specify software that is not installed by default. The ec2rl logic will ensure these programs are present and executable prior to running the module.
#### package
The software package an executable is from. This attribute is intended to provide extended details on the package that software comes with, including a URL to download or get further information from.
#### sudo
Indicates whether root/sudo is required to run the module. Use the values "True" or "False". You do not need to implement sudo checks in the script. If the value is "True" then the ec2rl logic will not run the module unless the executing user is root.
#### perfimpact
Indicates whether the module can hav`e significant performance impact upon the environment it is run. If the value is "True" then the module will be skipped if ec2rl was not given the "--perfimpact=true" argument.
#### parallelexclusive
Specifies a program that requires mutual exclusivity. For example, all modules specifying "bpf" will run in a serial manner.

### YAML
#### Syntax
1.  **---** The triple hyphen sequence denotes an explicit start of a document.
2.  **!ec2rlcore.module.Module** This tag tells the YAML parser which constructor to call when creating the object from the data stream. At the time of this writing, you can find the constructor inside module.py.
3.  **!!str** This tag tells YAML parser to not attempt to determine the type of the data and instead interpret it as a string literal
4.  **|** The pipe character tells the YAML parser the value is a literal-style scalar. In this case, the parser will include all whitespace. This is important for modules because indention and newline characters are kept. 

#### Miscellaneous
* **Indention** The YAML standard indent is two spaces which can be seen in the examples in this document. Be sure to maintain standard indention (e.g. four spaces for Python) for your script then indent the entire contents two spaces inside the module file.

## Example Module (mod.d/ps.yaml)
```
--- !ec2rlcore.module.Module
# Module document. Translates directly into an almost-complete Module object
name: !!str ps
version: !!str 1.0
title: !!str Collect output from ps for system analysis
helptext: !!str |
  Collect output from ps for system analysis
  Consumes --times= for number of times to repeat
  Consumes --period= for time period between repetition
placement: !!str run
package: 
  - !!str atop http://www.atoptool.nl/
language: !!str bash
content: !!str |
  # read-in shared function
  source functions.bash

  echo module-function has argv:  $0 "${@}"
  echo "I will collect ps output from this $EC2RL_DISTRO box for $times times every $period seconds."
  for i in $(seq 1 $times); do
      ps auxww
      sleep $period
  done
constraint:
  domain: !!str performance
  class: !!str collect
  distro: !!str alami ubuntu rhel suse
  required: !!str period times
  optional: !!str
  software: !!str ps
  sudo: !!str False
  perfimpact: !!str False
  parallelexclusive: !!str
```
# Additional Details
## Available Environment Variables
#### EC2RL_WORKDIR
The main tmp directory for the diagnostic tool. By default, /var/tmp/ec2rl
#### EC2RL_RUNDIR
The directory where all output will be stored. By default, /var/tmp/ec2rl/<date & time> - e.g. /var/tmp/ec2rl/2016-11-25T20_03_05.705430
#### EC2RL_GATHEREDDIR
The root directory for placing gather module data. By default, /var/tmp/ec2rl/<date & time>/mod_out/gathered/ - e.g. /var/tmp/ec2rl/2016-11-25T20_03_05.705430/mod_out/gathered
#### EC2RL_NET_DRIVER
The driver in use for the first alphabetically ordered non-virtual network interface on the instance. Examples include "xen_netfront", "ixgbevf", and "ena".
#### EC2RL_SUDO
True if ec2rl is running as root. False if not.
#### EC2RL_VIRT_TYPE
The virtualization type as provided by the instance metadata. Examples include "default-hvm" and "default-paravirtual".
#### EC2RL_INTERFACES
An enumerated list of interfaces on the system. String containing names, such as eth0, eth1, etc. This is generated via the functions.bash, 
and is only available for modules that have sourced it.
#### EC2RL_DISTRO
The detected distribution for the Linux system running ec2rl. One of alami, rhel, ubuntu, suse. 
## BASH ec2rl Function Library
### Inclusion
Include the following code snippet in BASH scripts to load in the ec2rl BASH function library.
```
# read-in shared function
source functions.bash
```
### Available Functions
Functions in the functions.bash
**logsearch**

```
Usage:
logsearch <locations> <search string> [grep opts]

Example:
logsearch "/var/log/messages* /var/log/syslog*" "panic" "-A30"

Args:
arg1 = File paths (required)
arg2 = Search pattern (required)
arg3 = Grep arguments (optional)
```
## Module Requirements
### Universal Requirements
1. Modules must always exit normally (e.g. exit 0) regardless of outcome. Modules must include the necessary error handling to meet this requirement.
2. All required and optional parameters must conform to ([a-z-0-9]+)=([a-z,-0-9]+) regex (this is param-name=paramvalue).
3. Ident loops and conditional statements.
4. Use four space indention unless otherwise required by the implementation language.
5. Modules must complete without any user intervention such as waiting for user input.
5. Modules must be tested for compatibility on the latest Amazon Machine Images (AMIs) of Amazon Linux, RHEL, SLES, and Ubuntu or as many as possible depending upon the intended operations performed.
### Diagnostic Module Requirements
1. A diagnostic module must print a status message.
   * A successful diagnostic should print a message prefixed with "[SUCCESS]".
   * A failing diagnostic should print a message prefixed with "[FAIL]".
   * A warning should print a message prefixed with "[WARN]".
2. A diagnostic module may include optional detail messages.
   * Detail messages are included in the run summary that is printed to standard output and are most useful when running the tool manually.
   * Detail messages must immediately follow the status message.
   * Detail messages must be prefixed with "--".
### Gather Module Requirements
1. Prefer copying a file rather than reading it.
2. Create a dir in $EC2RL_GATHEREDIR/modulename - e.g. $EC2RL_GATHEREDDIR/messages and copy the files into it.
### Python Module Requirements
1. Code must be compatible with and tested with both Python 2.7.9+ and 3.2+.
2. Code must only use the standard library.

## Module Run Order
Modules will run in the following order:

1. *prediagnostic* (stored in pre.d) - These modules are intended to be run to sanity-check the environment and gather any 
needed details for further use of the tool.
2. *diagnostic* (stored in mod.d) - These are the primary diagnostic, collection, and gathering modules that are used to collect data through the tool.
3. *postdiagnostic* (stored in post.d) - These are for analysis of the data gathered by the previously run modules, so as to automatically interpret
the output of previously run diagnostics.