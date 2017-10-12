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
Simple tarfile creator and s3 uploader.

Functions:
    make_tarfile: Compresses source_dir into output_filename
    s3upload: Uses requests to get a presigned URL and upload to s3 based on the a parameterized S3 uploader URL

Classes:
    None

Exceptions:
    S3UploadError: base error class for this module
    S3UploadUrlParsingFailure: raised when the support URL fails to be parsed
    S3UploadGetPresignedURLError: raised when a non-200 response is received from the uploader endpoint while attempting
    to obtain a presigned URL
    S3UploadResponseError: raised when a non-200 response is received when attempting to upload the archive file
    S3UploadTarfileReadError: raised when an error occurs reading the archive file
    S3UploadTarfileWriteError: raised when an error occurs writing to the archive file
"""
try:
    # Python 3
    import urllib
    import urllib.error
    import urllib.request as urllib_request
    urllib_urlopen = urllib.request.urlopen
    urllib_urlerror = urllib.error.URLError
    import urllib.parse as urlparse
except ImportError:  # pragma: no cover
    # Python 2
    import urllib2 as urllib
    import urllib2 as urllib_request
    urllib_urlopen = urllib.urlopen
    urllib_urlerror = urllib.URLError
    import urlparse


import json
import os
import requests
import tarfile

import ec2rlcore


def make_tarfile(output_filename, source_dir):
    """
    Given a source directory (source_dir) and a target file name (output_filename),
    create a gzipped tarball of the source_dir and name it output_filename.

    Parameters:
        output_filename (str): the name of tarball to be created
        source_dir (str): the directory that will be tar-ed up

    Returns:
        None
    """
    try:
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
    # IOError == OSError for Python >= 3.3
    except IOError as ioe:
        if ioe.errno == 2:
            raise S3UploadTarfileWriteError("ERROR: source directory '{}' does not exist.".format(source_dir))
        else:
            raise S3UploadTarfileWriteError("ERROR: there was an issue writing the file '{}'.".format(output_filename))
    # IOError != OSError for Python < 3.3
    except OSError as ose:  # pragma: no coverage
        if ose.errno == 2:
            raise S3UploadTarfileWriteError("ERROR: source directory '{}' does not exist.".format(source_dir))
        else:
            raise S3UploadTarfileWriteError("ERROR: there was an issue writing the file '{}'.".format(output_filename))


def get_presigned_url(uploader_url, filename, region="us-east-1"):
    """
    Given an uploader URL and a filename, parse the URL and get the presigned URL then use the presigned URL to upload
    the file named filename to S3.

    Parameters:
        uploader_url (str): the uploader URL provided by the AWS engineer
        filename (str): the file to be pushed to S3
        region (str): the S3 endpoint the file should be uploaded to

    Returns:
        presigned_url (str): the presigned URL as a string
    """
    endpoint = "https://30yinsv8k6.execute-api.us-east-1.amazonaws.com/prod/get-signed-url"

    s3uploader_regions = ["us-east-1", "eu-west-1", "ap-northeast-1"]
    if region not in s3uploader_regions:
        region = "us-east-1"

    query_str = urlparse.urlparse(uploader_url).query
    put_dict = urlparse.parse_qs(query_str)

    # If uploader_url is not parsable then maybe it is a shortened URL
    try:
        if not put_dict:
            the_request = urllib_request.Request(uploader_url)
            uploader_url = urllib_urlopen(the_request).geturl()
            query_str = urlparse.urlparse(uploader_url).query
            put_dict = urlparse.parse_qs(query_str)
    except urllib_urlerror:
        pass

    if put_dict:
        # urlparse.parse_qs returns dict values that are single value lists
        # Reassign the values to the first value in the list
        put_dict["accountId"] = put_dict["account-id"][0]
        put_dict["caseId"] = put_dict["case-id"][0]
        put_dict["key"] = put_dict["key"][0]
        put_dict["expiration"] = int(put_dict["expiration"][0])
        put_dict["fileName"] = filename
        put_dict["region"] = region
    else:
        raise S3UploadUrlParsingFailure(uploader_url)

    json_payload = json.dumps(put_dict)

    try:
        response = requests.post(url=endpoint, data=json_payload)
        # If the initial put was successful then proceed with uploading the file using the returned presigned URL
        if response.status_code == 200:
            presigned_url = response.text
            return presigned_url
        else:
            raise S3UploadGetPresignedURLError(response.status_code, uploader_url)
    except requests.exceptions.Timeout:
        raise requests.exceptions.Timeout("ERROR: Connection timed out.")


def s3upload(presigned_url, filename):
    """
    Given an uploader URL and a filename, parse the URL and get the presigned URL then use the presigned URL to upload
    the file named filename to S3.

    Parameters:
        presigned_url (str): the presigned URL that that is the PUT endpoint
        filename (str): the file to be pushed to S3

    Returns:
        (bool): True if the presigned URL was generated and the file uploaded successfully, else False.
    """
    import logging
    ec2rlcore.logutil.LogUtil.get_root_logger().addHandler(logging.NullHandler())
    try:
        # The response puts the URL string in double quotes so cut off the first and last characters
        with open(filename, "rb") as payload:
            response = requests.put(url=presigned_url, data=payload)
            if response.status_code == 200:
                ec2rlcore.dual_log("Upload successful")
                return True
            else:
                ec2rlcore.dual_log("ERROR: Upload failed.  Received response {}".format(
                    response.status_code))
                raise S3UploadResponseError(response.status_code)
    except requests.exceptions.Timeout:
        raise requests.exceptions.Timeout("ERROR: connection timed out.")
    except IOError:
        raise S3UploadTarfileReadError("ERROR: there was an issue reading the file '{}'.".format(filename))


class S3UploadError(Exception):
    """Base class for exceptions in this module."""
    pass


class S3UploadUrlParsingFailure(S3UploadError):
    """The support URL was not parsable."""
    def __init__(self, error_message, *args):
        message = "Failed to parse URL: {}".format(error_message)
        super(S3UploadUrlParsingFailure, self).__init__(message, *args)


class S3UploadGetPresignedURLError(S3UploadError):
    """The support URL was parseable, but a non-200 response was returned."""
    def __init__(self, status_code, support_url, *args):
        message = "Failed to get presigned URL. Received response '{}' for support URL '{}'".format(status_code,
                                                                                                    support_url)
        super(S3UploadGetPresignedURLError, self).__init__(message, *args)


class S3UploadResponseError(S3UploadError):
    """Requests received an invalid response."""
    def __init__(self, error_message, *args):
        message = "Received invalid response from URL: {}".format(error_message)
        super(S3UploadResponseError, self).__init__(message, *args)


class S3UploadTarfileReadError(S3UploadError):
    """An error occurred reading the tarball file."""
    def __init__(self, message, *args):
        super(S3UploadTarfileReadError, self).__init__(message, *args)


class S3UploadTarfileWriteError(S3UploadError):
    """An error occurred writing to the tarball file."""
    def __init__(self, message, *args):
        super(S3UploadTarfileWriteError, self).__init__(message, *args)
