# Copyright 2016-2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

"""Unit tests for "awshelpers" module."""
import unittest

from moto import mock_ec2
import boto3
import botocore
import mock
import requests
import responses

import ec2rlcore.awshelpers


@mock_ec2
class TestAwshelpers(unittest.TestCase):
    """Testing class for "awshelpers" unit tests."""
    IMDS_DOCUMENT = {'privateIp': '172.16.1.128', 'devpayProductCodes': None, 'marketplaceProductCodes': None,
                     'version': '2017-09-30', 'availabilityZone': 'us-east-1c', 'instanceId': 'i-deadbeef',
                     'billingProducts': None, 'instanceType': 'm5.4xlarge', 'kernelId': None, 'ramdiskId': None,
                     'accountId': '1234567890', 'architecture': 'x86_64', 'imageId': 'ami-deadbeef',
                     'pendingTime': '2018-09-14T01:58:16Z', 'region': 'us-east-1'}

    def setup_ec2(self):
        """Setup for usage, including moto environment."""
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
    def test_awshelpers_get_volume_ids(self):
        """Test that retrieving the volume ids for the instance works as expected."""
        instanceid = self.setup_ec2()
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=self.IMDS_DOCUMENT, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body=instanceid,
                      status=200)
        self.assertTrue(ec2rlcore.awshelpers.get_volume_ids())

    @responses.activate
    def test_awshelpers_get_volume_mappings(self):
        """Test that retrieving the volume mappings for the instance works as expected."""
        instanceid = self.setup_ec2()
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=self.IMDS_DOCUMENT, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body=instanceid,
                      status=200)
        self.assertTrue(ec2rlcore.awshelpers.get_volume_mappings())

    @responses.activate
    def test_awshelpers_get_instance_region(self):
        """Test that attempting to retrieve the instance region works as expected."""
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=self.IMDS_DOCUMENT, status=200)
        resp = ec2rlcore.awshelpers.get_instance_region()
        self.assertEqual(resp, "us-east-1")

    @responses.activate
    def test_awshelpers_get_instance_id(self):
        """Test that attempting to retrieve the instance id works as expected."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        resp = ec2rlcore.awshelpers.get_instance_id()
        self.assertEqual(resp, "i-deadbeef")

    @mock.patch("ec2rlcore.awshelpers.requests.get", side_effect=requests.exceptions.Timeout())
    def test_awshelpers_get_instance_region_timeout(self, mock_get):
        """Test that timeout exception raises as expected."""
        with self.assertRaises(ec2rlcore.awshelpers.AWSHelperMetadataTimeout):
            ec2rlcore.awshelpers.get_instance_region()
        self.assertTrue(mock_get.called)

    @mock.patch("ec2rlcore.awshelpers.requests.get", side_effect=requests.exceptions.Timeout())
    def test_awshelpers_get_instance_id_timeout(self, mock_get):
        """Test that timeout exception raises as expected."""
        with self.assertRaises(ec2rlcore.awshelpers.AWSHelperMetadataTimeout):
            ec2rlcore.awshelpers.get_instance_id()
        self.assertTrue(mock_get.called)

    @responses.activate
    def test_awshelpers_get_instance_region_httperror(self):
        """Test that get_instance_region raises AWSHelperMetadataHTTPError."""
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=self.IMDS_DOCUMENT, status=404)
        with self.assertRaises(ec2rlcore.awshelpers.AWSHelperMetadataHTTPError):
            ec2rlcore.awshelpers.get_instance_region()

    @responses.activate
    def test_awshelpers_get_instance_id_httperror(self):
        """Test that get_instance_id raises AWSHelperMetadataHTTPError."""
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=404)
        with self.assertRaises(ec2rlcore.awshelpers.AWSHelperMetadataHTTPError):
            ec2rlcore.awshelpers.get_instance_id()

    @mock.patch("ec2rlcore.awshelpers.requests.get", side_effect=requests.exceptions.RequestException())
    def test_awshelpers_get_instance_region_exception(self, mock_get):
        with self.assertRaises(ec2rlcore.awshelpers.AWSHelperRequestsException):
            ec2rlcore.awshelpers.get_instance_region()
            self.assertTrue(mock_get.called)

    @mock.patch("ec2rlcore.awshelpers.requests.get", side_effect=requests.exceptions.RequestException())
    def test_awshelpers_get_instance_id_exception(self, mock_get):
        with self.assertRaises(ec2rlcore.awshelpers.AWSHelperRequestsException):
            ec2rlcore.awshelpers.get_instance_id()
        self.assertTrue(mock_get.called)

    @mock.patch("ec2rlcore.awshelpers.boto3.client", side_effect=botocore.exceptions.NoCredentialsError())
    @responses.activate
    def test_awshelpers_no_creds_get_volume_mappings(self, mock_client):
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=self.IMDS_DOCUMENT, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        with self.assertRaises(ec2rlcore.awshelpers.AWSHelperNoCredsError):
            ec2rlcore.awshelpers.get_volume_mappings()
        self.assertTrue(mock_client.called)

    @mock.patch("ec2rlcore.awshelpers.boto3.client", side_effect=botocore.exceptions.NoCredentialsError())
    @responses.activate
    def test_awshelpers_no_creds_get_volume_id(self, mock_client):
        responses.add(responses.GET, "http://169.254.169.254/latest/dynamic/instance-identity/document",
                      json=self.IMDS_DOCUMENT, status=200)
        responses.add(responses.GET, "http://169.254.169.254/latest/meta-data/instance-id", body="i-deadbeef",
                      status=200)
        with self.assertRaises(ec2rlcore.awshelpers.AWSHelperNoCredsError):
            ec2rlcore.awshelpers.get_volume_ids()
        self.assertTrue(mock_client.called)
