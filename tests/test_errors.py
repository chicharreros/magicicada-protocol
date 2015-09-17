# -*- coding: utf-8 -*-
#
# Author: Natalia B. Bidart <natalia.bidart@canonical.com>
#
# Copyright (C) 2010-2012 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License version 3,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the
# OpenSSL library under certain conditions as described in each
# individual source file, and distribute linked combinations
# including the two.
# You must obey the GNU General Public License in all respects
# for all of the code used other than OpenSSL.  If you modify
# file(s) with this exception, you may extend this exception to your
# version of the file(s), but you are not obligated to do so.  If you
# do not wish to do so, delete this exception statement from your
# version.  If you delete this exception statement from all source
# files in the program, then also delete it here.
"""Tests for errors module."""

import unittest
import uuid

from ubuntuone.storageprotocol import errors, protocol_pb2

REQ_ARGS = dict(request=None, message=protocol_pb2.Message())

HIGH_LEVEL_ERRORS = {errors.StorageProtocolErrorSizeTooBig: dict(),
                     errors.StorageProtocolProtocolError: dict(),
                     errors.StorageRequestError: REQ_ARGS,
                     errors.RequestCancelledError: dict()}


class ErrorsTestCase(unittest.TestCase):
    """Basic testing of errors mapping."""

    def setUp(self):
        """Init."""

    def test_exceptions_are_storage_protocol_error(self):
        """High level exceptions inherit from StorageProtocolError."""
        for e, args in HIGH_LEVEL_ERRORS.iteritems():
            self.assertTrue(isinstance(e(**args), errors.StorageProtocolError),
                            "%r must inherit from StorageProtocolError" % e)

    def test_mapping(self):
        """Protocol's specific exceptions are correct."""
        for code_error, proto_error in errors._error_mapping.iteritems():
            self.assertTrue(isinstance(proto_error(**REQ_ARGS),
                            errors.StorageRequestError),
                            "%r must inherit from StorageRequestError" %
                             proto_error)
            self.assertEqual(proto_error,
                             errors.error_to_exception(code_error))

    def test_quota_exceed_error(self):
        """QuotaExceeded error must have quota info."""
        SHARE = uuid.uuid4()
        message = protocol_pb2.Message()
        message.error.type = protocol_pb2.Error.QUOTA_EXCEEDED
        message.free_space_info.share_id = str(SHARE)
        message.free_space_info.free_bytes = 10
        e = errors.QuotaExceededError(None, message)
        self.assertEqual(e.free_bytes, 10)
        self.assertEqual(e.share_id, SHARE)
