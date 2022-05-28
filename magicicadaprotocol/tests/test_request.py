# Copyright 2015-2022 Chicharreros (https://launchpad.net/~chicharreros)
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

"""Tests for directory content serialization/unserialization."""

import uuid

from twisted.internet import defer
from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase as TwistedTestCase

from magicicadaprotocol import errors, protocol_pb2
from magicicadaprotocol.request import (
    RequestHandler, Request, RequestResponse)


class MindlessRequest(Request):
    """A mindless Request which never actually does anything."""

    def _start(self):
        """Does nothing."""
        return getattr(self, 'start_result', None)


class MindlessRequestResponse(RequestResponse):
    """A mindless RequestResponse which never actually does anything."""

    def _start(self):
        """Does nothing."""
        return getattr(self, 'start_result', None)


class ConnectionLike(object):
    """An object vaguely resembling a FileDescriptor."""

    def __init__(self):
        """Initialize an instance."""
        self.producer = None

    def registerProducer(self, producer, streaming=False):
        """Fake registering a producer."""
        self.producer = producer

    def unregisterProducer(self):
        """Fake unregistering a producer."""
        self.producer = None


class TestRequest(TwistedTestCase):
    """Tests for Request."""

    timeout = 2

    @defer.inlineCallbacks
    def setUp(self):
        yield super(TestRequest, self).setUp()
        transport = ConnectionLike()
        protocol = RequestHandler()
        protocol.makeConnection(transport)
        self.request = MindlessRequest(protocol=protocol)
        self.error = None

    @defer.inlineCallbacks
    def test_disconnect_aborts_requests(self):
        """Test that disconnection aborts outstanding requests."""

        class OurException(RuntimeError):
            """An exception class to look for."""

        self.request.start()
        self.request.protocol.connectionLost(Failure(OurException()))
        try:
            yield self.request.deferred
        except OurException:
            pass  # passed
        else:
            self.fail("Expected to fail with the correct reason.")

    def test_default_process_message_basic(self):
        """_default_process_message maps errors to exceptions."""
        self.patch(self.request, 'error',
                   lambda error: setattr(self, 'error', error))

        message = protocol_pb2.Message()
        self.request._default_process_message(message)

        self.assertIsInstance(self.error, errors.StorageRequestError)
        self.assertEqual(self.request, self.error.request)
        self.assertEqual(message, self.error.error_message)

    def test_default_process_message_no_error_message(self):
        """_default_process_message maps errors to exceptions."""
        self.patch(self.request, 'error',
                   lambda error: setattr(self, 'error', error))

        message = protocol_pb2.Message()
        self.request._default_process_message(message)

        self.assertTrue(self.error.__class__ is errors.StorageRequestError)
        self.assertEqual(self.request, self.error.request)
        self.assertEqual(message, self.error.error_message)

    def test_default_process_message(self):
        """_default_process_message maps errors to exceptions."""
        self.patch(self.request, 'error',
                   lambda error: setattr(self, 'error', error))

        for code_error, proto_error in errors._error_mapping.items():
            message = protocol_pb2.Message()
            message.type = protocol_pb2.Message.ERROR
            message.error.type = code_error
            self.request._default_process_message(message)

            self.assertIsInstance(self.error, proto_error)
            self.assertEqual(self.request, self.error.request)
            self.assertEqual(message, self.error.error_message)

            self.error = None

    def test_start_returns_result(self):
        """Test start method returns result."""
        expected = object()
        self.request.start_result = expected
        actual = self.request.start()
        self.assertEqual(expected, actual, "start must return _start's result")

    def test_sendError(self):
        """Test for sendError message."""
        error_type = protocol_pb2.Error.QUOTA_EXCEEDED
        comment = 'No more bytes for you.'
        free_space_info = {'share_id': str(uuid.uuid4()), 'free_bytes': 0}
        self.request.id = 1

        def check(message):
            """Check the message"""
            self.assertEqual(message.id, self.request.id)
            self.assertEqual(message.type, protocol_pb2.Message.ERROR)
            self.assertEqual(message.error.type,
                             protocol_pb2.Error.QUOTA_EXCEEDED)
            self.assertEqual(message.error.comment, comment)
            self.assertEqual(message.free_space_info.free_bytes,
                             free_space_info['free_bytes'])
            self.assertEqual(message.free_space_info.share_id,
                             free_space_info['share_id'])
        self.patch(self.request, 'sendMessage', check)
        self.request.sendError(error_type, comment=comment,
                               free_space_info=free_space_info)


class TestRequestResponse(TestRequest):
    """Tests for RequestResponse."""

    @defer.inlineCallbacks
    def setUp(self):
        yield super(TestRequestResponse, self).setUp()
        message = protocol_pb2.Message()
        message.id = 1
        transport = ConnectionLike()
        protocol = RequestHandler()
        protocol.makeConnection(transport)
        self.request = MindlessRequestResponse(
            protocol=protocol, message=message)
        self.request.protocol.requests[message.id] = self.request
