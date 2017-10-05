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

"""Unit tests for "s3upload" module."""
try:
    # Python 2.x
    from cStringIO import StringIO
except ImportError:
    # Python 3.x
    from io import StringIO

try:
    # Python 3.x
    import urllib
    import urllib.error
    import urllib.request as urllib_request
    urllib_urlopen = urllib.request.urlopen
    urllib_urlopen_str = "urllib.request.urlopen"
    urllib_urlerror = urllib.error.URLError
except ImportError:
    # Python 2.x
    import urllib2 as urllib
    import urllib2 as urllib_request
    urllib_urlopen = urllib.urlopen
    urllib_urlopen_str = "urllib.urlopen"
    urllib_urlerror = urllib.URLError

import sys
import unittest

import mock
import requests
import responses

import ec2rlcore.s3upload

if sys.hexversion >= 0x3040000:
    # contextlib.redirect_stdout was introduced in Python 3.4
    import contextlib
else:
    # contextlib2 is a backport of contextlib from Python 3.5 and is compatible with Python2/3
    import contextlib2 as contextlib


class TestS3upload(unittest.TestCase):
    """Testing class for "s3upload" unit tests."""

    def setUp(self):
        self.output = StringIO()

    def tearDown(self):
        self.output.close()

    @responses.activate
    def test_s3upload_get_presigned_url(self):
        """Test that attempting to get a presigned url works as expected."""
        responses.add(responses.POST, "https://30yinsv8k6.execute-api.us-east-1.amazonaws.com/prod/get-signed-url",
                      body="http://test/", status=200)

        resp = ec2rlcore.s3upload.get_presigned_url("https://aws-support-uploader.s3.amazonaws.com/uploader?"
                                                    "account-id=9999999999&case-id=99999999&expiration=1486577795&"
                                                    "key=92e1ab350e7f5302551e0b05a89616381bb6c66"
                                                    "9c9492d9acfbf63701e455ef6", "test")

        self.assertEqual(resp, "http://test/")

    @responses.activate
    @mock.patch("ec2rlcore.s3upload.open")
    def test_s3upload(self, mock_read):
        """Test that attempting to upload works as expected."""
        responses.add(responses.PUT, "https://test", status=200)

        with contextlib.redirect_stdout(self.output):
            resp = ec2rlcore.s3upload.s3upload("https://test", "s3upload_test")
        self.assertEqual(self.output.getvalue(), "Upload successful\n")

        mock_read.assert_called_once_with("s3upload_test", "rb")
        self.assertTrue(resp)

    @mock.patch("ec2rlcore.s3upload.tarfile.open", create=True)
    def test_s3upload_make_tarfile(self, mock_tar_open):
        """Test that attempting to make a tarball works as expected."""
        ec2rlcore.s3upload.make_tarfile("tartest.tar.gz", "tartest_dir")

        mock_tar_open.assert_called_once_with("tartest.tar.gz", "w:gz")
        file_handle = mock_tar_open.return_value.__enter__.return_value
        file_handle.add.assert_called_once_with("tartest_dir", arcname="tartest_dir")

    @mock.patch("ec2rlcore.s3upload.tarfile.open", side_effect=IOError())
    def test_s3upload_make_tarfile_fail_generic_ioe(self, mock_tar_open):
        """Test handling of an IOError that isn't errno=2."""
        with self.assertRaises(ec2rlcore.s3upload.S3UploadTarfileWriteError):
            ec2rlcore.s3upload.make_tarfile("tartest.tar.gz", "tartest_dir")

        mock_tar_open.assert_called_once_with("tartest.tar.gz", "w:gz")
        file_handle = mock_tar_open.return_value.__enter__.return_value
        file_handle.add.assert_not_called()

    @mock.patch("ec2rlcore.s3upload.tarfile.open", side_effect=IOError(2, "No such file or directory"))
    def test_s3upload_make_tarfile_fail_ioe_fnfe(self, mock_tar_open):
        """Test handling of an IOError a missing source directory."""
        with self.assertRaises(ec2rlcore.s3upload.S3UploadTarfileWriteError):
            ec2rlcore.s3upload.make_tarfile("tartest.tar.gz", "tartest_dir")

        mock_tar_open.assert_called_once_with("tartest.tar.gz", "w:gz")
        file_handle = mock_tar_open.return_value.__enter__.return_value
        file_handle.add.assert_not_called()

    @mock.patch("ec2rlcore.s3upload.tarfile.open", side_effect=OSError())
    def test_s3upload_make_tarfile_fail_generic_oserror(self, mock_tar_open):
        """Test handling of an IOError that isn't errno=2."""
        with self.assertRaises(ec2rlcore.s3upload.S3UploadTarfileWriteError):
            ec2rlcore.s3upload.make_tarfile("tartest.tar.gz", "tartest_dir")

        mock_tar_open.assert_called_once_with("tartest.tar.gz", "w:gz")
        file_handle = mock_tar_open.return_value.__enter__.return_value
        file_handle.add.assert_not_called()

    @mock.patch("ec2rlcore.s3upload.tarfile.open", side_effect=OSError(2, "No such file or directory"))
    def test_s3upload_make_tarfile_fail_oserror_fnfe(self, mock_tar_open):
        """Test handling of an OSError a missing source directory."""
        with self.assertRaises(ec2rlcore.s3upload.S3UploadTarfileWriteError):
            ec2rlcore.s3upload.make_tarfile("tartest.tar.gz", "tartest_dir")

        mock_tar_open.assert_called_once_with("tartest.tar.gz", "w:gz")
        file_handle = mock_tar_open.return_value.__enter__.return_value
        file_handle.add.assert_not_called()

    @mock.patch("ec2rlcore.s3upload.requests.put", side_effect=requests.exceptions.Timeout())
    @mock.patch("ec2rlcore.s3upload.open")
    def test_s3upload_timeout(self, mock_open, mock_put):
        """Test that timeout exception is raised as expected."""
        with self.assertRaises(ec2rlcore.s3upload.requests.exceptions.Timeout):
            ec2rlcore.s3upload.s3upload("https://test", "s3upload_test")

        self.assertTrue(mock_open.called)
        self.assertTrue(mock_put.called)

    @mock.patch("ec2rlcore.s3upload.requests.post", side_effect=requests.exceptions.Timeout())
    def test_s3upload_presigned_url_timeout(self, mock_post):
        with self.assertRaises(ec2rlcore.s3upload.requests.exceptions.Timeout):
            ec2rlcore.s3upload.get_presigned_url("https://aws-support-uploader.s3.amazonaws.com/uploader?"
                                                 "account-id=9999999999&case-id=99999999&expiration=1486577795&"
                                                 "key=92e1ab350e7f5302551e0b05a89616381bb6c66"
                                                 "9c9492d9acfbf63701e455ef6", "test")

        self.assertTrue(mock_post.called)

    @mock.patch("ec2rlcore.s3upload.open", side_effect=IOError())
    def test_s3upload_ioerror(self, mock_open):
        """Test that IOerror exception is raised as expected."""
        with self.assertRaises(ec2rlcore.s3upload.S3UploadTarfileReadError):
            ec2rlcore.s3upload.s3upload("https://test", "s3upload_test")

        self.assertTrue(mock_open.called)

    @responses.activate
    def test_s3upload_get_presigned_url_fail(self):
        """Test that attempting to get a presigned url works as expected."""
        with self.assertRaises(ec2rlcore.s3upload.S3UploadGetPresignedURLError):
            responses.add(responses.POST, "https://30yinsv8k6.execute-api.us-east-1.amazonaws.com/prod/get-signed-url",
                          body="{'errorMessage': 'not found'}", status=404, content_type="application/json")

            ec2rlcore.s3upload.get_presigned_url("https://aws-support-uploader.s3.amazonaws.com/uploader?"
                                                 "account-id=9999999999&case-id=99999999&expiration=1486577795&"
                                                 "key=92e1ab350e7f5302551e0b05a89616381bb6c66"
                                                 "9c9492d9acfbf63701e455ef6", "test")

    @mock.patch(urllib_urlopen_str, side_effect=urllib_urlerror(reason="Test"))
    def test_s3upload_get_presigned_url_bad_url(self, mock_urllib):
        """Test that obtaining the real url of a non-real URL leads to an S3UploadUrlParsingFailure exception."""
        with self.assertRaises(ec2rlcore.s3upload.S3UploadUrlParsingFailure):
            ec2rlcore.s3upload.get_presigned_url("http://fakeurl.asdf123", "test")

    @responses.activate
    @mock.patch("ec2rlcore.s3upload.open")
    def test_s3upload_fail(self, mock_open):
        """Test that attempting to upload works as expected."""
        responses.add(responses.PUT, "https://test", body="{'message': 'not found'}", status=404,
                      content_type="application/json")
        with self.assertRaises(ec2rlcore.s3upload.S3UploadResponseError):
            with contextlib.redirect_stdout(self.output):
                ec2rlcore.s3upload.s3upload("https://test", "s3upload_test")
        self.assertEqual(self.output.getvalue(), "ERROR: Upload failed.  Received response 404\n")
        self.assertTrue(mock_open.called)

    @responses.activate
    def test_s3upload_get_presigned_url_bad_region(self):
        """Test that the region parser provides a valid default region when an invalid region used."""
        import json
        responses.add(responses.POST, "https://30yinsv8k6.execute-api.us-east-1.amazonaws.com/prod/get-signed-url",
                      body="http://test/", status=200)

        ec2rlcore.s3upload.get_presigned_url("https://aws-support-uploader.s3.amazonaws.com/uploader?"
                                             "account-id=9999999999&case-id=99999999&expiration=1486577795&"
                                             "key=92e1ab350e7f5302551e0b05a89616381bb6c66"
                                             "9c9492d9acfbf63701e455ef6", "test", "in-valid-1")

        request = json.loads(responses.calls[0].request.body)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual("us-east-1", request["region"])

    @responses.activate
    def test_s3upload_get_presigned_url_good_region(self):
        """Test that the region parser provides a valid region."""
        import json
        responses.add(responses.POST, "https://30yinsv8k6.execute-api.us-east-1.amazonaws.com/prod/get-signed-url",
                      body="http://test/", status=200)

        ec2rlcore.s3upload.get_presigned_url("https://aws-support-uploader.s3.amazonaws.com/uploader?"
                                             "account-id=9999999999&case-id=99999999&expiration=1486577795&"
                                             "key=92e1ab350e7f5302551e0b05a89616381bb6c66"
                                             "9c9492d9acfbf63701e455ef6", "test", "eu-west-1")

        request = json.loads(responses.calls[0].request.body)
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual("eu-west-1", request["region"])
