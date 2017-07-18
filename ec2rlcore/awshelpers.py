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

"""
Various helper functions for dealing with AWS resources

Functions:
    get_instance_region: Gets the region of the currently running instance
    get_instance_id: Gets the instance ID of the currently running instance
    get_volume_ids: Creates a list of ebs volumes attached to the instance
    get_volume_mappings: Creates a dict of unix block device : ebs volume id

Classes:
    None

Exceptions:
    AWSHelperError: base error class for this module
    AWSHelperMetadataTimeout: raised when a timeout occurs while attempting to reach the metadata service
    AWSHelperMetadataHTTPError: raised when an HTTP error occurs while attempting to interact with the metadata service
    AWSHelperRequestsException: raised when an ambiguous error occurs while attempting to interact with the metadata
    service
    NoCredsError: raised no AWS credentials were found
"""

import requests
import botocore
import boto3


def get_instance_region():
    """
    Gets the region of the currently running instance

    Returns:
        Region (str): Region of the currently running instance
    """
    try:
        r = requests.get("http://169.254.169.254/latest/meta-data/placement/availability-zone")
        r.raise_for_status()
        return r.text[:-1]
    except requests.exceptions.Timeout:
        raise AWSHelperMetadataTimeout()
    except requests.exceptions.HTTPError as err:
        raise AWSHelperMetadataHTTPError(err.response.status_code)
    except requests.exceptions.RequestException as err:
        raise AWSHelperRequestsException(err)


def get_instance_id():
    """
    Gets the instance ID of the currently running instance

    Returns:
        instance_id (str): Instance ID of the currently running instance
    """
    try:
        r = requests.get("http://169.254.169.254/latest/meta-data/instance-id")
        r.raise_for_status()
        return r.text
    except requests.exceptions.Timeout:
        raise AWSHelperMetadataTimeout()
    except requests.exceptions.HTTPError as err:
        raise AWSHelperMetadataHTTPError(err.response.status_code)
    except requests.exceptions.RequestException as err:
        raise AWSHelperRequestsException(err)


def get_volume_ids():
    """
    Creates a list of the ebs volumes attached to the instances

    Returns:
        volume_ids (list): List of instance ebs volumes
    """
    try:

        client = boto3.client("ec2", region_name=get_instance_region())

        response = client.describe_instances(
            DryRun=False,
            InstanceIds=[
                get_instance_id()
            ]
        )

        volume_ids = [i["Ebs"]["VolumeId"] for i in response["Reservations"][0]["Instances"][0]["BlockDeviceMappings"]
                      if "Ebs" in i]

        del client

    except botocore.exceptions.NoCredentialsError:
        raise AWSHelperNoCredsError

    return volume_ids


def get_volume_mappings():
    """
    Creates a dict of block device mappings:ebs volume id

    Returns:
        volume_mappings (dict): Dict of block device mapping:ebs volume id
    """

    try:
        client = boto3.client("ec2", region_name=get_instance_region())

        response = client.describe_instances(
            DryRun=False,
            InstanceIds=[
                get_instance_id()
            ]
        )

        volume_mappings = {i["DeviceName"]: i["Ebs"]["VolumeId"] for i in
                           response["Reservations"][0]["Instances"][0]["BlockDeviceMappings"] if "Ebs" in i}

        del client

    except botocore.exceptions.NoCredentialsError:
        raise AWSHelperNoCredsError

    return volume_mappings


class AWSHelperError(Exception):
    """Base class for exceptions in this module."""

    pass


class AWSHelperMetadataTimeout(AWSHelperError):
    """A timeout occurred while attempting to interact with the metadata service."""

    def __init__(self):
        super(AWSHelperMetadataTimeout, self).__init__("Timeout received when querying the metadata service.")


class AWSHelperMetadataHTTPError(AWSHelperError):
    """An HTTP error occurred while attempting to interact with the metadata service."""

    def __init__(self, error_code):
        message = "HTTP Error received from the metadata service: {}".format(error_code)
        super(AWSHelperMetadataHTTPError, self).__init__(message)


class AWSHelperRequestsException(AWSHelperError):
    """A Requests exception was raised while attempting to interact with the metadata service."""

    def __init__(self, error):
        message = "Unknown error in the request: {}".format(error)
        super(AWSHelperRequestsException, self).__init__(message)


class AWSHelperNoCredsError(AWSHelperError):
    """No AWS credentials were found."""

    def __init__(self):
        message = "No AWS Credentials configured. Please configure these and try again"
        super(AWSHelperNoCredsError, self).__init__(message)
