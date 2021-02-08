# Copyright 2016-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""
Unit tests for the enadiag module
"""
import os
import subprocess
import sys
import unittest

import mock

import moduletests.src.enadiag

try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib

class Testenadiag(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    def test_get_interfaces(self):
        with mock.patch("moduletests.src.enadiag.os.listdir") as mock_dir:
            mock_dir.return_value = ["eth0", "eth1", "lo"]
            self.assertEquals(moduletests.src.enadiag.get_interfaces(),["eth0", "eth1"])

    def test_get_interfaces_empty_list(self):
        with mock.patch("moduletests.src.enadiag.os.listdir") as mock_dir:
            mock_dir.return_value = ["lo"]
            with contextlib.redirect_stdout(self.output):
                with self.assertRaises(ValueError) as ex:
                    interfaces = moduletests.src.enadiag.get_interfaces()
                    self.assertEqual(self.output.getvalue(),"[WARN] No interfaces found")
                    self.assertEqual(len(interfaces), 0)

    @mock.patch("moduletests.src.enadiag.os.listdir", side_effect=OSError)
    def test_get_interfaces_os_error(self, mock_listdir):
        with contextlib.redirect_stdout(self.output):
            interfaces = moduletests.src.enadiag.get_interfaces()
            self.assertEqual(self.output.getvalue(),"[WARN] Unable to build interface list.\n")
            self.assertEqual(len(interfaces), 0)
            self.assertTrue(mock_listdir.called)

    def test_get_ena_version(self):
        open_mock = mock.mock_open(read_data="2.2.4g\n")
        # mock_open does not have support for iteration so it must be added manually
        # readline() until a blank line is reached (the sentinel)

        def iter_func(self):
            return iter(self.readline, "")
        open_mock.return_value.__iter__ = iter_func

        def py3_next_func(self):
            return next(iter(self.readline, ""))

        if sys.hexversion >= 0x3000000:
            open_mock.return_value.__next__ = py3_next_func

        with mock.patch("moduletests.src.enadiag.os.listdir") as mock_dir:
            mock_dir.return_value = ["eth0"]
            with mock.patch("moduletests.src.enadiag.open", open_mock) as mock_open:
                self.assertEquals(moduletests.src.enadiag.get_ena_version(),"2.2.4g")
            self.assertTrue(open_mock.called)

    def test_get_ena_version_unknown(self):
        with mock.patch("moduletests.src.enadiag.os.listdir") as mock_dir:
            mock_dir.return_value = []
            with contextlib.redirect_stdout(self.output):
                with self.assertRaises(ValueError) as ex:
                    moduletests.src.enadiag.get_ena_version()
                    self.assertEqual(self.output.getvalue(),"[WARN] ENA driver version is Unknown. Unable to proceed.")

    @mock.patch("moduletests.src.enadiag.os.listdir", side_effect=OSError)
    def test_get_ena_version_os_error(self, mock_listdir):
        with self.assertRaises(ValueError) as ex:
            moduletests.src.enadiag.get_ena_version()
            self.assertEquals(ex, "[WARN] ENA driver version is Unknown. Unable to proceed.")
            self.assertTrue(mock_listdir.called)

    @mock.patch("moduletests.src.enadiag.get_ena_version", return_value="2.2.15g")
    def test_compare_ena_version(self, mock_getver):
        self.assertTrue(moduletests.src.enadiag.compare_ena_version())

    @mock.patch("moduletests.src.enadiag.get_ena_version", return_value="2.2.4g")
    def test_compare_ena_version_old(self, mock_getver):
        self.assertFalse(moduletests.src.enadiag.compare_ena_version())

    @mock.patch("subprocess.check_output")
    def test_get_ena_stats(self, mock_check_ouput):
        mock_check_ouput.return_value="     tx_timeout: 0\n     suspend: 0\n     wd_expired: 0\n     " \
                                      "interface_down: 0\n     admin_q_pause: 0\n     bw_in_allowance_exceeded: 0\n" \
                                      "     bw_out_allowance_exceeded: 0\n     pps_allowance_exceeded: 0\n" \
                                      "     conntrack_allowance_exceeded: 0\n     linklocal_allowance_exceeded: 0\n"
        ethtool_output="     tx_timeout: 0\n     suspend: 0\n     wd_expired: 0\n     interface_down: 0\n" \
                       "     admin_q_pause: 0\n     bw_in_allowance_exceeded: 0\n     bw_out_allowance_exceeded: 0\n" \
                       "     pps_allowance_exceeded: 0\n     conntrack_allowance_exceeded: 0\n" \
                       "     linklocal_allowance_exceeded: 0\n"
        self.assertEquals(moduletests.src.enadiag.get_ena_stats("eth0"), ethtool_output)

    @mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(
        "1", "test", "bash: ethtool: command not found"))
    def test_get_ena_stats_cpe(self, mock_check_output):
        with contextlib.redirect_stdout(self.output):
            with self.assertRaises(Exception) as ex:
                moduletests.src.enadiag.get_ena_stats("eth0")
                self.assertIn("[WARN] Unable to get stats from ethool.", self.output.getvalue())


    @mock.patch("moduletests.src.enadiag.get_ena_stats")
    def test_save_ena_stats(self, mock_get_ena_stats):
        interfaces = ["eth0"]
        mock_get_ena_stats.return_value="     tx_timeout: 1\n     suspend: 0\n     wd_expired: 0\n     " \
                                        "interface_down: 0\n     admin_q_pause: 0\n     bw_in_allowance_exceeded: 0\n" \
                                        "     bw_out_allowance_exceeded: 0\n     pps_allowance_exceeded: 0\n" \
                                        "     conntrack_allowance_exceeded: 0\n     linklocal_allowance_exceeded: 0\n"
        results = [moduletests.src.enadiag.Interface(name) for name in interfaces]
        moduletests.src.enadiag.save_ena_stats(results)

        eth0 = results[0]
        self.assertEqual(results[0].name, "eth0")
        self.assertEqual(results[0].tx_timeout, "1")
        self.assertEqual(len(results), 1)

    @mock.patch("moduletests.src.enadiag.get_ena_stats")
    def test_save_ena_stats_exception(self, mock_get_ena_stats):
        interfaces = ["eth0"]
        mock_get_ena_stats.return_value="     tx_timrtheout: 0\n     suspend: 0\n     wd_expirrthed: 0\n     " \
                                        "interface_drown: 0\n     admin__pause: 0\n     bw_inht_allowce_exceeded: 0\n" \
                                        "     bw_out_allrhtowance_exceeded: 0\n     pps_allowance_xceeded: 0\n" \
                                        "     conntrack_allowance_htrexceeded: 0\n     lilocal_allohrtnce_exceeded: 0\n"
        results = [moduletests.src.enadiag.Interface(name) for name in interfaces]
        with contextlib.redirect_stdout(self.output):
            with self.assertRaises(Exception) as ex:
                moduletests.src.enadiag.save_ena_stats(results)
                self.assertEqual(self.output.getvalue(),"[WARN] Unable to save interface stats to class object. Ethtool output changed?")

    def test_diagnose_stats_problems(self):
        with contextlib.redirect_stdout(self.output):
            eth1 = moduletests.src.enadiag.Interface(
                name = "eth1",
                tx_timeout = 1,
                suspend = 1,
                wd_expired = 1,
                interface_down = 0,
                admin_q_pause = 1,
                bw_in_allowance_exceeded = 1,
                bw_out_allowance_exceeded = 1,
                pps_allowance_exceeded = 1,
                conntrack_allowance_exceeded = 1,
                linklocal_allowance_exceeded = 1
            )
            moduletests.src.enadiag.diagnose_stats(eth1)
            self.assertEqual(self.output.getvalue(), "[FAILURE] ENA problems found on eth1.\n     1 "
                                                     "tx_timeout events found.\n     1 suspend events found.\n    1 " \
                                                     "wd_expired events found.\n    1 admin_q_pauses found.\n    1 " \
                                                     "bw_in_allowance_exceeded events found.\n    1 " \
                                                     "bw_out_allowance_exceeded events found.\n    1 " \
                                                     "pps_allowance_exceeded events found.\n    1 " \
                                                     "conntrack_allowance_exceeded events found.\n    1 " \
                                                     "linklocal_allowance_exceeded events found.\n" \
                                                     "Please visit https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/" \
                                                     "troubleshooting-ena.html for more details on stat counters.\n")

    def test_diagnose_stats_no_problems(self):
        with contextlib.redirect_stdout(self.output):
            eth2 = moduletests.src.enadiag.Interface(
                name = "eth2",
                tx_timeout = 0,
                suspend = 0,
                wd_expired = 0,
                interface_down = 0,
                admin_q_pause = 0,
                bw_in_allowance_exceeded = 0,
                bw_out_allowance_exceeded = 0,
                pps_allowance_exceeded = 0,
                conntrack_allowance_exceeded = 0,
                linklocal_allowance_exceeded = 0
            )
            moduletests.src.enadiag.diagnose_stats(eth2)
            self.assertEqual(self.output.getvalue(), "[SUCCESS] No ENA problems found on eth2.\n")

    def test_diagnose_stats_exception(self):
        with contextlib.redirect_stdout(self.output):
            eth3 = moduletests.src.enadiag.Interface(
                name = "eth3",
                tx_timeout = "abc",
            )
            moduletests.src.enadiag.diagnose_stats(eth3)
            self.assertIn("[WARN] Unable to diagnose interface stats.", self.output.getvalue())

    def test_diagnose_stats_warnings_problems(self):
        with contextlib.redirect_stdout(self.output):
            eth4 = moduletests.src.enadiag.Interface(
                name = "eth4",
                tx_timeout = 1,
                suspend = 1,
                wd_expired = 1,
                interface_down = 1,
                admin_q_pause = 1,
                bw_in_allowance_exceeded = 1,
                bw_out_allowance_exceeded = 1,
                pps_allowance_exceeded = 1,
                conntrack_allowance_exceeded = 1,
                linklocal_allowance_exceeded = 1
            )
            moduletests.src.enadiag.diagnose_stats(eth4)
            self.assertEqual(self.output.getvalue(), "[FAILURE] ENA problems found on eth4.\n     1 tx_timeout events "
                                                     "found.\n     1 suspend events found.\n    1 wd_expired events "
                                                     "found.\n    1 admin_q_pauses found.\n    1 "
                                                     "bw_in_allowance_exceeded events found.\n    1 "
                                                     "bw_out_allowance_exceeded events found.\n    1 "
                                                     "pps_allowance_exceeded events found.\n    1 "
                                                     "conntrack_allowance_exceeded events found.\n    1 "
                                                     "linklocal_allowance_exceeded events found.\n[WARN] Potential ENA "
                                                     "problems found on eth4. \n    1 interface_down events found.\n    "
                                                     "If you have not up/downed the interface this could be a link flap."
                                                     "\n\nPlease visit https://docs.aws.amazon.com/AWSEC2/latest/"
                                                     "UserGuide/troubleshooting-ena.html for more details on stat "
                                                     "counters.\n")


    def test_diagnose_stats_warnings(self):
        with contextlib.redirect_stdout(self.output):
            eth5 = moduletests.src.enadiag.Interface(
                name = "eth5",
                tx_timeout = 0,
                suspend = 0,
                wd_expired = 0,
                interface_down = 1,
                admin_q_pause = 0,
                bw_in_allowance_exceeded = 0,
                bw_out_allowance_exceeded = 0,
                pps_allowance_exceeded = 0,
                conntrack_allowance_exceeded = 0,
                linklocal_allowance_exceeded = 0
            )
            moduletests.src.enadiag.diagnose_stats(eth5)
            self.assertEqual(self.output.getvalue(), "[WARN] Potential ENA problems found on eth5. \n    1 "
                                                     "interface_down events found.\n    "
                                                     "If you have not up/downed the interface this could be a link "
                                                     "flap.\n\nPlease visit https://docs.aws.amazon.com/AWSEC2/latest/"
                                                     "UserGuide/troubleshooting-ena.html for more details on "
                                                     "stat counters.\n")

    @mock.patch("moduletests.src.enadiag.compare_ena_version", return_value="True")
    @mock.patch("moduletests.src.enadiag.get_interfaces", return_value=["eth0"])
    @mock.patch("moduletests.src.enadiag.get_ena_stats")
    def test_run(self, mock_version, mock_interfaces, mock_get_ena_stats):
        mock_get_ena_stats.return_value="     tx_timeout: 0\n     suspend: 0\n     wd_expired: 0\n     " \
                                        "interface_down: 0\n     admin_q_pause: 0\n     bw_in_allowance_exceeded: 0\n" \
                                        "     bw_out_allowance_exceeded: 0\n     pps_allowance_exceeded: 0\n" \
                                        "     conntrack_allowance_exceeded: 0\n     linklocal_allowance_exceeded: 0\n"
        with contextlib.redirect_stdout(self.output):
            moduletests.src.enadiag.run()
            self.assertIn("[SUCCESS] No ENA problems found on eth0.\n", self.output.getvalue())

    @mock.patch("moduletests.src.enadiag.get_ena_version", return_value="1.2.15g")
    def test_run_old_version(self, mock_version):
        with contextlib.redirect_stdout(self.output):
            moduletests.src.enadiag.run()
            self.assertEqual(self.output.getvalue(), "[WARNING] ENA driver too old to get statistics.\n")

    @mock.patch("moduletests.src.enadiag.run", side_effect=Exception)
    def test_run_exception(self, mock_run):
        with contextlib.redirect_stdout(self.output):
            with self.assertRaises(Exception) as ex:
                moduletests.src.enadiag.run()
                self.assertIn("[WARN] Unable to run ENA stats module.", self.output.getvalue())
