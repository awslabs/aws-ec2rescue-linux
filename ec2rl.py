# Copyright 2016-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""ec2rl:  A frame for executing diagnostic and troubleshooting
        modules for analyzing issues on Linux instances on AWS.

USAGE:
    ec2rl [subcommand] [parameters]

COMMANDS:
The following are the accepted subcommands:
    run     - executes modules
    list    - list available modules for platform
    help    - print long help

run:
    SYNOPSIS:
        ec2rl run [--only-modules=MODULEa ... MODULEx] [--only-domains=DOMAINa ... DOMAINx]
        ec2rl run [--xyz=param] [--no=xyz]

    DESCRIPTION:
        The run command executes any ec2rl modules specified,
        or attempts all if no restrictions are set.
        Only modules who have their necessary parameters will actually be run.

    OPTIONS:
        Switch Parameters:
            --xyz       - pass 'xyz' variables to modules, set to true
                          enable modules with name or aspect of 'xyz'
            --no=xyz    - pass 'xyz' variable to modules, set to false
                          disable modules with name or aspect of 'xyz'
        Key/Value Parameters:
            --abc=efg   - pass variable 'abc' to modules, set to 'efg'
                          to satisfy module constraints
            --only-modules=module1,module2 - only run modules in the
                          specified comma delimited list
            --only-domains=domain1,domain2 - only run the domains in the
                          specified comma delimited list

list:
    SYNOPSIS:
        ec2rl list

    DESCRIPTION:
        The list command provides a full list of the available modules that can be ran.

help:
    SYNOPSIS:
        ec2rl help [SUBCOMMANDa ... SUBCOMMANDx]
        ec2rl help [--only-modules=MODULEa ... MODULEx] [--only-domains=DOMAINa ... DOMAINx]

    DESCRIPTION:
        Provides help details on the specified module(s) and/or subcommand(s).

    OPTIONS:
        Key/Value Parameters:
            --only-modules=module1,module2 - only provides help for modules in the
            specified comma delimited list
            --only-domains=domain1,domain2 - only provides help for domains in the
            specified comma delimited list

SPECIAL:
    A small number of options that have special meaning to the ec2rl framework
    and are not passed to modules.

    OPTIONS:
        --file=<filename>   - loads a pre-configured file of Run settings
        --pdb               - run framework inside the Python Debugger
"""

from __future__ import print_function
import platform
import pdb
import signal
import sys


def main():
    """
    Create the ec2rl instance and run it. Provide the user with messages relevant to their subcommand, if applicable.

    Returns:
        (int): 0 if no errors detected,
        201 if Python < 2.7,
    """

    if sys.hexversion < 0x2070000:
        print("ec2rl requires Python 2.7+, but running version is {0}.".format(
            platform.python_version()))
        return 201

    import ec2rlcore.main
    ec2rl = ec2rlcore.main.Main()
    ec2rl()

    return 0


def pdb_signal_handler(signal_num, stack_frame):
    print("Received signal: {}".format(signal_num))
    pdb.Pdb().set_trace(stack_frame)

if __name__ == "__main__":
    if "--pdb" in sys.argv:
        sys.argv.remove("--pdb")
        sys.exit(pdb.run("main()"))
    else:
        # SIGUSR1 is POSIX signal 10
        signal.signal(signal.SIGUSR1, pdb_signal_handler)
        sys.exit(main())
