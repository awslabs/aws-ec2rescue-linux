# conntrackfull module

## Problem Description

The netfilter connection tracking table (nf_conntrack) becomes full, preventing new connections from being established by the instance.  This can cause intermittent connectivity loss, problems accessing websites and services hosted by the instance, and trouble establishing a SSH connection to the instance.  Established connections should continue functioning without issues, as their connection tracking entries are already created.

## Diagnosing with EC2 Rescue for Linux

The EC2 Rescue for Linux tool (ec2rl) can check kernel logs for messages indicating the netfilter conntrack tables have filled.  The diagnostic module is named 'conntrackfull' and will run with the default set of modules when running 'ec2rl run'.  If you wish to run the conntrackfull module individually, the command below can be used.

```commandline
$ ./ec2rl run --only-modules=conntrackfull
```

Passing example:

```commandline
----------[Diagnostic Results]----------
module run/conntrackfull         [SUCCESS] No conntrack table full errors found.
```

Failing example:

```commandline
----------[Diagnostic Results]----------
module run/conntrackfull         [FAILURE] Conntrack table full errors found. 2 occurrences in dmesg"
```

## Manual Diagnosis

To manually check if the netfilter conntrack table has filled, dmesg logs can be searched using 'grep' to find the pattern 'table full, dropping packet'.  Searching dmesg logs will locate any occurrences of the table filling since the last boot of the instance.  To search further back, the operating system's log files must be searched instead.

```commandline
$ dmesg | grep 'table full, dropping packet'
```

The conntrack entries in the /proc tree are only populated if conntrack is active.  The default configuration on Amazon Linux and other distributions does not require conntrack to be enabled, thus the entries may not be present.  If conntrack is not enabled, the table cannot be full.  To check the maximum and current conntrack entries:

```commandline
sysctl net.netfilter.nf_conntrack_max net.netfilter.nf_conntrack_count
```

If the nf_conntrack_count is near nf_conntrack_max, then the maximum may need to be increased.

## Resolution

There are many tuning options for the netfilter module, maximum table size, number of buckets, timeouts, etc.  To increase the size of the netfilter conntrack tables without altering the timeout or connection handling behavior, the maximum entries and number of buckets should be increased.

The following two commands will double the size of the default conntrack tables and buckets immediately.  nf_conntrack_buckets should be set to nf_conntrack_max / 4 for most use cases.

```commandline
sudo sysctl -w net.netfilter.nf_conntrack_max=131072
sudo sysctl -w net.netfilter.nf_conntrack_buckets=32768
```

If satisfied with the increased conntrack table size, you can make the changes persistent by adding those entries to sysctl.conf:

```commandline
echo "net.netfilter.nf_conntrack_max=131072" | sudo tee -a /etc/sysctl.d/99-netfilter.conf
echo "net.netfilter.nf_conntrack_buckets=32768" | sudo tee -a /etc/sysctl.d/99-netfilter.conf
```

The default timeout parameters are generally correct for most use cases, though you may wish to reduce some timeouts to better match connection patterns in extreme situations.  Extreme caution should be used when reducing close_wait and time_wait.  Below are the default timeout parameters:

```commandline
net.netfilter.nf_conntrack_generic_timeout = 600
net.netfilter.nf_conntrack_icmp_timeout = 30
net.netfilter.nf_conntrack_tcp_timeout_close = 10
net.netfilter.nf_conntrack_tcp_timeout_close_wait = 60
net.netfilter.nf_conntrack_tcp_timeout_established = 432000
net.netfilter.nf_conntrack_tcp_timeout_fin_wait = 120
net.netfilter.nf_conntrack_tcp_timeout_last_ack = 30
net.netfilter.nf_conntrack_tcp_timeout_max_retrans = 300
net.netfilter.nf_conntrack_tcp_timeout_syn_recv = 60
net.netfilter.nf_conntrack_tcp_timeout_syn_sent = 120
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 120
net.netfilter.nf_conntrack_tcp_timeout_unacknowledged = 300
net.netfilter.nf_conntrack_udp_timeout = 30
net.netfilter.nf_conntrack_udp_timeout_stream = 180
```