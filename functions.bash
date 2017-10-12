#!/bin/bash

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

##
## shared functions and boilerplate for ec2rl modules
## - improve readability of functions
## - reduce duplicated code
## - 
##

## disable some bash builtins to clear the namespace
enable -n help

## debug printing
shopt -s expand_aliases
alias log='echo '
alias error='>&4 echo "Error: ${__name__}:"'
if $DEBUG; then
  alias debug='>&4 '
else
  alias debug='#'
fi

## set common variables by reading from modules' comment-block
__name__=${0##*/}
__list__="$(awk -F '#Q# ' '/^#Q#/{print $2}' ${0})"
__help__="$(awk -F '#H# ' '/^#H#/{print $2}' ${0})"

##
## logsearch
##
## Searches files in given location for a pattern. 
## Automatically detects compression and decompresses as needed
## Returns nothing if no results found
##
## Usage:
## logsearch <locations> <search string> [grep opts]
##
## Example:
## logsearch "/var/log/messages* /var/log/syslog*" "panic" "-A30" 
##
## arg1 = filepaths (required)
## arg2 = search pattern (required)
## arg3 = grep arguments (optional)

function logsearch {

    if test -z "$1"; then
        echo "No search locations given"
        return 1
    fi

    if test -z "$2"; then
        echo "No search pattern given"
        return 2
    fi

    local filepaths=$1
    local pattern=$2
    local grepargs="$3"

    for filename in $filepaths; do
        if [ -e $filename ] && [ -r $filename ]; then
            #file exists and is readable
            local filetype=$(file $filename)

            #This is where additional compression types should be added
            case $filetype in
                *gzip*)
                    if zgrep -v \/zgrep\  $filename | zgrep $grepargs "$pattern" >/dev/null 2>&1; then
                        echo -e "Match found in $filename"
                        zgrep $grepargs "$pattern" $filename
                    fi ;;
                *xz*)
                    if grep -v \/xzgrep\  $filename | xzgrep $grepargs "$pattern" >/dev/null 2>&1; then
                        echo -e "Match found in $filename"
                        xzgrep $grepargs "$pattern" $filename
                    fi ;;
                *)
                    #assume uncompressed
                    if grep -v \/grep\  $filename | grep $grepargs "$pattern" >/dev/null 2>&1; then
                        echo -e "Match found in $filename"
                        grep $grepargs "$pattern" $filename
                    fi ;;
            esac
            
        fi
    done

    # Disabled journal searching due to performance impact
    # if which journalctl >/dev/null 2>&1; then
    #     if journalctl -ql | grep -v \/grep\ | grep $grepargs "$pattern" >/dev/null 2>&1; then
    #         echo -e "Match found in systemd journal"
    #         journalctl -ql | grep -v \/grep\ | grep $grepargs "$pattern"
    #     fi
    # fi
}

##
## $EC2RL_INTERFACES
## Enumerates all of the interfaces on a device minus loopback
##

EC2RL_INTERFACES="$(find /sys/class/net/* | awk -F'/' '!/lo/ {print $5}')"
