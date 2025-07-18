=======
# EC2 Rescue for Linux v1.1.8

#### General

#### Framework

#### Module

# EC2 Rescue for Linux v1.1.7

#### General
* [Enhancement] Alter method to determine if the Operating Systems is Amazon Linux 2023 to catch all versions.

#### Framework

#### Modules
* [New Module] Add nvidiabugreport collect module

# EC2 Rescue for Linux v1.1.6

#### General
* [Enhancement] Add rpm output to build process
* [Enhancement] Add support for RHEL 8.x, Ubuntu 22.10, SLES 15, Amazon Linux 2023
* [Enhancement] Add support for Python 3.7 to 3.10+
* [Enhancement] Re-enable journal logsearch bash function as logsearch_with_journal

#### Framework

#### Modules
* [Misc] Create Ubuntu specific copies of bcc modules to reflect the Debian package adding -bpfcc to the binary file names.
* [New Module] Add enadiag net diagnostic module.
* [Enhancement] Re-enable journal module with safer defaults and additional options for selecting time range, logs gathered, and output format.
* [Enhancement] Add logsearch_with_journal support for hungtasks, kernelbug, kerneldereference, kernelpanic, oomkiller, softlockup diagnostic modules.
* [Bugfix] Fix alami2 search messages in kernelbug, kerneldereference, kernelpanic, oomkiller, softlockup diagnostic modules.
* [New Module] Add sosreport os gather module.
* [New Module] Add supportconfig os gather module.

#### Testing
* [Bugfix] Update requirements_test.txt to lock versions of transient dependencies causing issues for py2.7 builds

# EC2 Rescue for Linux v1.1.5

#### General
* [Enhancement] Updated vendored version of boto3 to 1.12.6
* [Enhancement] Updated vendored version of botocore to 1.15.6
* [Enhancement] Add urllib3 version 1.25.9 to vended packages

#### Framework
* [Enhancement] Refactor get_instance_region() to utilize identity document.
* [Enhancement] Add is_nitro() function to determine if instance is Nitro or bare-metal
* [Bugfix] Fix is_an_instance() inaccurately categorized Nitro instances as not-an-instance.
* [Bugfix] Fix EC2RL_VIRT_TYPE not taking into account change in metadata profile display of Nitro instances
* [Enhancement] Modified get_instance_region() and get_instance_id() to support IMDSv2.
* [Enhancement] Modified verify_metadata(), get_virt_type() and is_an_instance() to support IMDSv2

#### Modules
* [New Module] Add lvmarchives module.
* [Bugfix] Update xennetrocket, xenfeatures, ixgbevfversion to reflect proper EC2RL_VIRT_TYPE detection.
* [New Module] Add dmesg collect module, rename old dmesg gather module to dmesgfiles. Output between the two is different and necessitates an additional module.
* [New Module] Add cron gather module.
* [New Module] Add numastat collect module.
* [New Module] Add bccmysqldqslower performance module
* [New Module] Add amazonlinuxextras os collect module.
* [New Module] Add kpatch os collect module.
* [New Module] Add yumconfiguration os collect module.
* [New Module] Add xennetsgmtu net diagnostic module.
* [Enhancement] Add user exclude list to OpenSSH module, add non-ssh user ssm-user to exclude list.
* [Enhancement] Update OpenSSH module to account for new OpenSSH packaging in ALAMI2.

#### Testing
* [New Test] Add unit tests for is_nitro() function
* [Enhancement] Lock down the versions of setuptools and mock for Python 2.7 as the maintainers have discontinued support for Python 2.

# EC2 Rescue for Linux v1.1.4

#### General
* None

#### Framework
* [Enhancement] Added --output-dir option.
* [Enhancement] Updated Linux distribution detection to support the latest system-release string in Amazon Linux 2.

#### Modules
* [Enhancement] Updated iproute module to collect additional route table details.
* [Enhancement] Added all supported distros to bcc modules.
* [New Module] Added kernel page table isolation module.
* [New Module] Added retpoline module.
* [New Module] Added networkmanagerstatus module.
* [New Module] Added systemsmanager module.

#### Testing
* None

# EC2 Rescue for Linux v1.1.3

#### General
* [Enhancement] Added pull request template with license wording.
* [Enhancement] Added bundledpython Makefile target to create releases with a bundled copy of Python as an alternative to the binary build.
* [Enhancement] Added several multi-action Makefile targets to simplify the CodeBuild buildspec.
* [Enhancement] Updated CodeBuild buildspec to source make args from the environment.
* [Enhancement] Added GPG signature verification details to README.
* [Enhancement] Added bundled build details to README.
* [Enhancement] Updated example configs to include run subcommand.
* [Enhancement] Added new example configs for remediation oriented tasks.
* [Bugfix] Added missing license files for vendored copies of pyyaml and requests.

#### Framework
* [Enhancement] Options class: Added support for providing a comma delimited list of exclusions with the --no argument.
* [Enhancement] Main, ModuleDir classes: Merged all module validation tasks into one location.
* [Enhancement] Binary build: include the requests certificate bundle to ensure SSL works.
* [Enhancement] The prep Makefile target now removes the bin directory.
* [Enhancement] Updated distribution detection for the Amazon Linux 2 LTS release.
* [Enhancement] Make the vendored Python modules available to EC2RL modules via PYTHONPATH.
* [Enhancement] Updated the ec2rl script to use a local copy of Python, if present. The local path for the local copy must be python/bin/python. This change is primarily intended to support the bundled build.

#### Modules
* [Enhancement] arpcache, arpignore, tcprecycle: standardized detection method to not assume the parameter exists in the running kernel.
* [Enhancement] Rewrote kernelconfig to gather the three most recently modified kernel configuration files from /boot plus the running kernel configuration if it is not amongst the initial three gathered configurations.
* [New Module] Added dhclientleases module with remediation support.
* [New Module] Added dpkgpackages module.
* [New Module] Added rpmpackages module.
* [New Module] Added workspacelogs module.
* [New Module] Added localtime module.
* [New Module] Added kerberosconfig module.
* [New Module] Added libtirpcnetconfig module.

#### Testing
* None

# EC2 Rescue for Linux v1.1.2

#### General
* [Bugfix] Updated included SSM documents to accommodate ec2rl directory name with version number
* [Enhancement] Updated vendored version of botocore to 1.9.1

#### Framework
* [Enhancement] Added lib directory to PATH for Python-based EC2RL modules that require access to vendored modules
* [Enhancement] Framework now returns a non-zero status code when the subcommand fails
* [Enhancement] Updated get_distro to accommodate CentOS 6 system-release version strings.
* [Enhancement] ModuleDir class: Added clear method
* [Bugfix] ModuleDir class: Updated _unmap_module method because some mappings were not being updated
* [Bugfix] Module class: Removed unsuable environment variable, EC2RL_MODULE_PATH, which was exported by the run method

#### Modules
* [New Feature] openssh: Added support for generation of a new RSA keypair. The new private key is stored as an SSM SecureString Parameter
* [Enhancement] openssh: Refactored key injection to support key injection as a standalone action
* [Enhancement] openssh: Modified method by which the privilege separation directory is obtained to support older distributions
* [Bugfix] rebuildinitrd: Added missing dracut kernel version argument

#### Testing
* [Enhancement] Updated test runner script, run_module_unit_tests.py, to show missing coverage in test report
* [Enhancement] Updated Makefile to support Python 2 in the "binary" and "test" targets
* [Bugfix] Changed a side_effect exception from FileNotFoundError to IOError because FileNotFoundError does not exist in Python 2

# EC2 Rescue for Linux v1.1.1

#### General
* None

#### Framework
* [Bugfix] Fixed regression where permission mode on WORKDIR was not being set to 0o777

#### Modules
* None

#### Testing
* [Bugfix] Renamed test with duplicate name

# EC2 Rescue for Linux v1.1.0

#### General
* [New Feature] Added remediation support to the framework and modules, including 8 new or refactored modules which remediate issues
* [Enhancement] Updated modules to support instances running on the Nitro hypervisor
* [Enhancement] Added support for Amazon Linux AMI v2
* [Enhancement] Added sha256 hashes for downloadable tarballs

#### Framework
* [New Feature] Added a set of generic functions, including backup and restore functions, for use in Python-based modoules
* [New Feature] Added is_an_instance() to determine if the machine ec2rl is being run on is an ec2 instance
* [New Feature] Added remediation module support
* [Enhancement] Added support for ALAMI v2
* [Enhancement] Limited permission on the RUNDIR to only the creator
* [Enhancement] Set upper bound of 100 to concurrency value
* [Enhancement] Refactored prediag.get_distro() for readability
* [Enhancement] Added subprocess universal_newlines arg to module run to simplify handling of output
* [Enhancement] Consolidated the files produced during the binary build to accommodate modules using vendored non-standard libraries
* [Enhancement] Reformatted output from the list subcommand to include a remediation support column
* [Bugfix] Corrected string matching for pruning modules

#### Modules
* [New Feature] Added remediation module template
* [New Module] Added openssh module with remediation support (complete rework of previous SSH module)
* [New Module] Added udevnetpersistent module with remediation support
* [New Module] Added selinuxpermissive module with remediation support (intended for non-booting/inaccessible instances)
* [New Module] Added rebuildinitrd module with remediation support (intended for non-booting/inaccessible instances)
* [New Module] Added fstabfailures module with remediation support (intended for non-booting/inaccessible instances)
* [Enhancement] Added Nitro/KVM support to ixgbevf, xenfeatures, xennetrocket modules
* [Enhancement] Refactored tcprecycle module and added remediation support
* [Enhancement] Refactored arpignore module and added remediation support
* [Enhancement] Refactoredarpcache module and added remediation support
* [Bugfix] Corrected description of bccvfsstat module
* [Bugfix] Corrected typos in bcctcpretrans module
* [Bugfix] Added --preserve-status to all BASH-based modules utilizing "timeout"

#### Testing
* [New Test] Added unit and function tests for openssh module
* [New Test] Added unit tests for udevnetpersistent module
* [New Test] Added unit tests for selinuxpermissive module
* [New Test] Added unit tests for rebuildinitrd module
* [New Test] Added unit tests for fstabfailures module
* [New Test] Added unit tests for tcprecycle module
* [New Test] Added unit tests for arpignore module
* [New Test] Added unit tests for arpcache module
* [Enhancement] Added a repr test for programversion
* [Enhancement] Added check to assert that RUNDIR is created with 0o700 permissions
* [Bugfix] Added missing mocks for several tests
