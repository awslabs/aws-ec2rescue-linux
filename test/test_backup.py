# Copyright 2016-2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

"""Unit tests for "backup" module."""
try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

import re
import sys
import unittest

import boto3
import botocore
import mock
import moto
import responses

import ec2rlcore.awshelpers
import ec2rlcore.backup

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib


@moto.mock_ec2
class TestBackup(unittest.TestCase):
    """Testing class for "backup" unit tests."""
    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    def setup_ec2(self):
        """
        Setting up for usage, including moto environment
        """
        ec2 = boto3.client("ec2", region_name="us-east-1")

        response = ec2.run_instances(
            ImageId="ami-deadbeef",
            MinCount=1,
            MaxCount=1,
            KeyName="deadbeef",
            InstanceType="m4.16xlarge",
        )
        instance = response["Instances"][0]
        instanceid = instance["InstanceId"]

        return instanceid

    @responses.activate
    def test_backup_snapshot(self):
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        instanceid = self.setup_ec2()
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body=instanceid,
                      status=200)
        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rlcore.backup.create_all_snapshots(ec2rlcore.awshelpers.get_volume_ids()))
        self.assertTrue(re.match(r"^Creating snapshot snap-[a-z0-9]{8} for volume vol-[a-z0-9]{8}$",
                                 self.output.getvalue(), re.M))

    @responses.activate
    def test_backup_image(self):
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        instanceid = self.setup_ec2()
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body=instanceid,
                      status=200)

        with contextlib.redirect_stdout(self.output):
            self.assertTrue(ec2rlcore.backup.create_image(ec2rlcore.awshelpers.get_instance_id()))
        self.assertTrue(re.match(r"^Creating AMI ami-[a-z0-9]{8} for i-[a-z0-9]{8}$",
                                 self.output.getvalue(), re.M))

    @mock.patch("ec2rlcore.backup.boto3.client", side_effect=botocore.exceptions.NoCredentialsError())
    @responses.activate
    def test_backup_nocreds_snapshot(self, mock_client):
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)

        with self.assertRaises(ec2rlcore.backup.BackupNoCredsError):
            ec2rlcore.backup.create_all_snapshots(["vol-deadbeef"])

        self.assertTrue(mock_client.called)

    @mock.patch("ec2rlcore.backup.boto3.client", side_effect=botocore.exceptions.NoCredentialsError())
    @responses.activate
    def test_backup_nocreds_image(self, mock_client):
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)

        with self.assertRaises(ec2rlcore.backup.BackupNoCredsError):
            ec2rlcore.backup.create_image(ec2rlcore.awshelpers.get_instance_id())

        self.assertTrue(mock_client.called)

    @mock.patch("ec2rlcore.backup.boto3.client", side_effect=botocore.exceptions.ClientError(
        {"Error": {"Code": "ErrorCode", "Message": "Error Message"}}, "test"))
    @responses.activate
    def test_backup_clienterror_snapshot(self, mock_client):
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)

        with self.assertRaises(ec2rlcore.backup.BackupClientError):
            ec2rlcore.backup.create_all_snapshots(["vol-deadbeef"])

        self.assertTrue(mock_client.called)

    @mock.patch("ec2rlcore.backup.boto3.client", side_effect=botocore.exceptions.ClientError(
        {"Error": {"Code": "500", "Message": "Error"}}, "test"))
    @responses.activate
    def test_backup_clienterror_image(self, mock_client):
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)

        with self.assertRaises(ec2rlcore.backup.BackupClientError):
            ec2rlcore.backup.create_image(ec2rlcore.awshelpers.get_instance_id())

        self.assertTrue(mock_client.called)

    @mock.patch("ec2rlcore.backup.boto3.client", side_effect=TypeError)
    @responses.activate
    def test_backup_typeerror_snapshot(self, mock_client):
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)

        with self.assertRaises(ec2rlcore.backup.BackupSpecificationError):
            ec2rlcore.backup.create_all_snapshots(["vol-deadbeef"])

        self.assertTrue(mock_client.called)

    @mock.patch("ec2rlcore.backup.boto3.client", side_effect=TypeError)
    @responses.activate
    def test_backup_typeerror_image(self, mock_client):
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)

        with self.assertRaises(ec2rlcore.backup.BackupSpecificationError):
            ec2rlcore.backup.create_image(ec2rlcore.awshelpers.get_instance_id())

        self.assertTrue(mock_client.called)

    @mock.patch("ec2rlcore.backup.describe_image_status", side_effect=["failed"])
    @responses.activate
    def test_backup_image_error(self, mock_describe_image_status):
        instanceid = self.setup_ec2()
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body=instanceid,
                      status=200)

        with self.assertRaises(ec2rlcore.backup.BackupImageError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.backup.create_image(ec2rlcore.awshelpers.get_instance_id())
            self.assertTrue(re.match(r"^Creating AMI ami-[a-z0-9]{8} for i-[a-z0-9]{8}$",
                                     self.output.getvalue(), re.M))

        self.assertTrue(mock_describe_image_status.called)

    @mock.patch("ec2rlcore.backup.describe_snapshot_status", side_effect=["error"])
    @responses.activate
    def test_backup_snapshot_error(self, mock_describe_snapshot_status):
        document = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                    'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                    'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                    'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                    'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}
        instanceid = self.setup_ec2()
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=document, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body=instanceid,
                      status=200)

        with self.assertRaises(ec2rlcore.backup.BackupSnapshotError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.backup.create_all_snapshots(ec2rlcore.awshelpers.get_volume_ids())
            self.assertTrue(re.match(r"^Creating snapshot snap-[a-z0-9]{8} for volume vol-[a-z0-9]{8}$",
                                     self.output.getvalue(), re.M))

        self.assertTrue(mock_describe_snapshot_status.called)
