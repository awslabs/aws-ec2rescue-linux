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
Creates snapshots of volumes or an AMI of the instance for backup purposes prior to running the tool.

Functions:
    snapshot: Takes a snapshot of a volume given its volume ID
    create_all_snapshots: Creates snapshots of all volumes in the given list
    create_image: Creates an AMI of an instance given its instance ID
    describe_snapshot_status: Returns the state of a snapshot given its snapshot ID
    describe_image_status: Returns the state of an image given its image ID

Classes:
    None

Exceptions:
    BackupError: base error class for this module
    BackupNoCredsError: raised when boto fails to find a set of configured credentials
    BackupClientError: raised when boto raises a ClientError
    BackupSpecificationError: raised when an invalid instance or volume ID is specified
    BackupSnapshotError: raised when a snapshot is found to be in an 'error' state
    BackupImageError: raised when an image is found to be in an 'error' state
"""
from __future__ import print_function
import datetime
import botocore
import boto3

import ec2rlcore
import ec2rlcore.awshelpers


def snapshot(volume_id):
    """
    Given a volume ID, take a snapshot of the volume, and return the new snapshot's ID.

    Params:
        volume_id (str): volume_id to take a snapshot of

    Returns:
        snapshot_id (str): snapshot_id created
    """

    try:
        client = boto3.client("ec2", region_name=ec2rlcore.awshelpers.get_instance_region())

        response = client.create_snapshot(
            DryRun=False,
            VolumeId=volume_id,
            Description="EC2 Rescue for Linux Created Snapshot for " + volume_id + " at " +
            datetime.datetime.utcnow().strftime("%Y/%m/%d %H-%M-%S")
        )

        ec2rlcore.dual_log("Creating snapshot " + response["SnapshotId"] + " for volume " + volume_id)

        if describe_snapshot_status(response["SnapshotId"]) == "error":
            raise BackupSnapshotError

        del client

    except botocore.exceptions.NoCredentialsError:
        raise BackupNoCredsError
    except botocore.exceptions.ClientError as error:
        raise BackupClientError(error.response)
    except TypeError:
        raise BackupSpecificationError

    return response["SnapshotId"]


def create_all_snapshots(volume_ids):
    """
    Creates the snapshots of all volumes in the provided list.

    Params:
        volume_ids (list): List of volumes attached to the instance

    Returns:
        None
    """
    for i in volume_ids:
        snapshot(i)
    return True


def create_image(instance_id):
    """
    Creates an image of the provided instance.

    Params:
        instance_id (str): instance to take an image of

    Returns:
       response["ImageId"] (str): imageid created
    """
    try:
        client = boto3.client("ec2", region_name=ec2rlcore.awshelpers.get_instance_region())

        response = client.create_image(
            DryRun=False,
            InstanceId=instance_id,
            Name="EC2RL backup of " + instance_id + " at " + datetime.datetime.utcnow().strftime("%Y/%m/%d %H-%M-%S"),
            Description="EC2 Rescue for Linux Created AMI for " + instance_id,
            NoReboot=True
        )

        ec2rlcore.dual_log("Creating AMI " + response["ImageId"] + " for " + instance_id)

        if describe_image_status(response["ImageId"]) in ("invalid", "deregistered", "failed"):
            raise BackupImageError

        del client

    except botocore.exceptions.NoCredentialsError:
        raise BackupNoCredsError
    except botocore.exceptions.ClientError as error:
        raise BackupClientError(error.response)
    except TypeError:
        raise BackupSpecificationError

    return response["ImageId"]


def describe_snapshot_status(snapshotid):
    """
    Obtains the snapshot's status with a describe call then returns status.

    Params:
        snapshotid (str): snapshot to get the status of

    Returns:
        snapshot_status (str): status of the snapshot
    """
    client = boto3.client("ec2", region_name=ec2rlcore.awshelpers.get_instance_region())

    response = client.describe_snapshots(
        DryRun=False,
        SnapshotIds=[
            snapshotid
        ]
    )

    snapshot_status = response["Snapshots"][0]["State"]

    return snapshot_status


def describe_image_status(imageid):
    """
    Obtains the image's status with a describe call then returns status.

    Params:
        imageid (str): image to get the status of

    Returns:
        image_status (str): status of the image
    """
    client = boto3.client("ec2", region_name=ec2rlcore.awshelpers.get_instance_region())

    response = client.describe_images(
        DryRun=False,
        ImageIds=[
            imageid
        ]
    )

    image_status = response["Images"][0]["State"]

    return image_status


class BackupError(Exception):
    """Base class for exceptions in this module."""
    pass


class BackupNoCredsError(BackupError):
    """No AWS credentials were found."""
    def __init__(self):
        message = "No AWS Credentials configured. Please configure them and try again."
        super(BackupNoCredsError, self).__init__(message)


class BackupClientError(BackupError):
    """A Clienterror was raised by boto."""
    def __init__(self, message):
        super(BackupClientError, self).__init__(message)


class BackupSpecificationError(BackupError):
    """Invalid Block Device Mapping or Volume Specification Error."""
    def __init__(self):
        message = "Please make sure you have properly specified your block device mapping or volume IDs." \
                  "This includes not specifying instance store volumes."
        super(BackupSpecificationError, self).__init__(message)


class BackupSnapshotError(BackupError):
    """Snapshot is an 'error' state."""
    def __init__(self):
        message = "Snapshot failed and is in error state. Please try again."
        super(BackupSnapshotError, self).__init__(message)


class BackupImageError(BackupError):
    """Image is in an 'error' state."""
    def __init__(self):
        message = "Image failed and is in error state. Please try again."
        super(BackupImageError, self).__init__(message)
