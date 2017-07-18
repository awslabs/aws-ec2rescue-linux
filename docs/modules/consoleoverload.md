# consoleoverload module

## Problem Description

EC2 instances may throttle the serial console output if the instance is sending too much data to the serial console.  If this throttling occurs, the instance may hang until the message can be written to the console, leading to poor performance and potentially crash.  When this throttling occurs, a message will be logged in dmesg stating "too much work for irq4".

## Detecting with EC2 Rescue for Linux

EC2 Rescue for Linux includes a diagnostic module which will search for occurrences of serial console throttling in the available kernel logs.  This is provided by the 'consoleoverload' diagnostic module.  This module will run by default with or without sudo access, and can be run individually

```commandline
$ ./ec2rl run --only-modules=consoleoverload
```

Passing output:

```commandline
----------[Diagnostic Results]----------
module run/consoleoverload              [SUCCESS] No serial console overload found
```

Failing output:

```commandline
----------[Diagnostic Results]----------
module run/consoleoverload       [FAILURE] Serial console overload found. 3 occurrences in dmesg
```

## Detecting Manually

This throttling can be detected by checking the dmesg output within the operating system.  The grep utility can be used to easily search the active dmesg logs to quickly identify if throttling has occurred.
```
$ dmesg | grep "too much work for irq4"
```
If any results are returned, serial console throttling has occurred.

## Resolution

To avoid throttling, the instance should be configured to send less data to the serial console. The majority of console messages are sent via syslog services, primarily rsyslogd.  Some services, iptables for example, will send a high volume of log messages via rsyslogd which get forwarded to the console.  To reduce the number of messages sent to the console via rsyslogd, the log level can be adjusted in /etc/rsyslogd.conf.

In /etc/rsyslogd.conf, add the following line under the global directives section.  If a klogConsoleLogLevel line is present, modify the existing value instead.

```commandline
$klogConsoleLogLevel 4
```

After making the change to rsyslogd.conf, you must reload the configuration for the change to take effect

```commandline
$ sudo service rsyslog reload
```

For high volume logging, we recommend forwarding logs to a log management service such as CloudWatch Logs instead of logging application messages directly to the serial console.  The netconsole system can be used to help debug kernel level issues which would otherwise generate too much traffic to the serial console, or when the serial console is otherwise not suitable.