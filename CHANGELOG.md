# EC2 Rescue for Linux v1.1.3

#### General
* [Enhancement] Added pull request template with license wording.
* [Enhancement] Added nightly, nightlybinary, and nightyall Makefile targets to simplify the CodeBuild buildspec.
* [Enhancement] Updated CodeBuild buildspec to source make args from the environment.

#### Framework
* [Enhancement] Options class: Added support for providing a comma delimited list of exclusions with the --no argument.
* [Enhancement] Main, ModuleDir classes: Merged all module validation tasks into one location.
* [Enhancement] Binary build: include the requests certificate bundle to ensure SSL works.
* [Enhancement] The prep Makefile target now removes the bin directory.
* [Enhancement] Updated distribution detection for the Amazon Linux 2 LTS release.

#### Modules
* [Enhancement] arpcache, arpignore, tcprecycle: standardized detection method to not assume the parameter exists in the running kernel. 
* [New Module] Added dhclientleases module with remediation support.
* [New Module] Added dpkgpackages module.
* [New Module] Added rpmpackages module.

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
