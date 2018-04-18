# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2012 Canonical Ltd.
# Copyright 2015-2018 Chicharreros (https://launchpad.net/~chicharreros)
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

"""Tests for PutContent request."""

import unittest

from StringIO import StringIO

from mocker import Mocker, ANY
from twisted.test.proto_helpers import StringTransport

from magicicadaprotocol import protocol_pb2, request
from magicicadaprotocol.client import PutContent, StorageClient


class TestOffset(unittest.TestCase):
    """Tests for BEGIN_CONTENT's offset attribute."""

    def setUp(self):
        super(TestOffset, self).setUp()
        transport = StringTransport()
        self.protocol = StorageClient()
        self.protocol.transport = transport

    def test_offset(self):
        """
        Test that, if the server's BEGIN_CONTENT message specifies an offset,
        the file to be uploaded is seek'ed to the right position.
        """
        offset = 23
        mocker = Mocker()
        transport = mocker.mock()
        transport.registerProducer(ANY, streaming=True)
        transport.write(ANY)
        mocker.count(1, None)  # I don't really care how many times
        fd = mocker.mock()
        fd.seek(offset)  # this is really all I care about
        fd.read(ANY)
        mocker.result('')
        mocker.replay()

        protocol = StorageClient()
        protocol.transport = transport
        pc = PutContent(protocol, 'share', 'node', '', '', 0, 0, 0, fd)
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.BEGIN_CONTENT
        message.begin_content.offset = offset
        pc.start()
        pc.processMessage(message)

    def test_offset_none(self):
        """
        Test that, if the server's BEGIN_CONTENT message does *not* specify an
        offset, the file to be uploaded is seek'ed to the right position.
        """
        mocker = Mocker()
        transport = mocker.mock()
        transport.registerProducer(ANY, streaming=True)
        transport.write(ANY)
        mocker.count(1, None)  # I don't really care how many times
        fd = mocker.mock()
        fd.seek(0)  # this is really all I care about
        fd.read(ANY)
        mocker.result('')
        mocker.replay()

        protocol = StorageClient()
        protocol.transport = transport
        pc = PutContent(protocol, 'share', 'node', '', '', 0, 0, 0, fd)
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.BEGIN_CONTENT
        pc.start()
        pc.processMessage(message)

    def test_callback(self):
        """Test that, if the server specify an offset, we call back with it."""
        upload_id = 'foo'
        offset = 123456
        called = []
        pc = PutContent(self.protocol, 'share', 'node', '', '', 0, 0, 0,
                        StringIO(''), upload_id_cb=lambda *a: called.append(a))
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.BEGIN_CONTENT
        message.begin_content.upload_id = upload_id
        message.begin_content.offset = offset
        pc.start()
        pc.processMessage(message)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0], (upload_id, offset))


class TestUploadId(unittest.TestCase):
    """Tests for BEGIN_CONTENT and PUT_CONTENT upload_id attribute."""

    def setUp(self):
        super(TestUploadId, self).setUp()
        transport = StringTransport()
        self.protocol = StorageClient()
        self.protocol.transport = transport

    def test_server_upload_id(self):
        """Test that, if the server specify an upload_id, we save it."""
        upload_id = "foo"
        called = []
        pc = PutContent(self.protocol, 'share', 'node', '', '', 0, 0, 0,
                        StringIO(''), upload_id_cb=lambda *a: called.append(a))
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.BEGIN_CONTENT
        message.begin_content.upload_id = upload_id
        message.begin_content.offset = 0
        pc.start()
        pc.processMessage(message)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0], ('foo', 0))

    def test_server_upload_id_no_cb(self):
        """Test that, if the server specify an upload_id, we save it.

        Only if we have the upload_id_cb defined.
        """
        offset = 23
        # just to check something
        mocker = Mocker()
        fd = mocker.mock()
        fd.seek(offset)  # this is really all I care about
        fd.read(ANY)
        mocker.result('')
        mocker.replay()

        upload_id = "foo"
        pc = PutContent(self.protocol, 'share', 'node', '', '',
                        0, 0, 0, fd)
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.BEGIN_CONTENT
        message.begin_content.upload_id = upload_id
        message.begin_content.offset = offset
        pc.start()
        pc.processMessage(message)

    def test_server_upload_id_none(self):
        """Test that if there is no upload_id we ignore it."""
        called = []
        pc = PutContent(self.protocol, 'share', 'node', '', '',
                        0, 0, 0, StringIO(''), upload_id_cb=called.append)
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.BEGIN_CONTENT
        pc.start()
        pc.processMessage(message)
        self.assertEqual(len(called), 0)

    def test_client_upload_id(self):
        """Test that, we send the upload id to the server."""
        pc = PutContent(self.protocol, 'share', 'node', '', '',
                        0, 0, 0, StringIO(''), upload_id='foo')
        pc.start()
        pc_msg = protocol_pb2.Message()
        data = self.protocol.transport.value()
        pc_msg.ParseFromString(data[request.SIZE_FMT_SIZE:])
        self.assertEqual(pc_msg.put_content.upload_id, 'foo')

    def test_magic_hash_something(self):
        """Send magic hash in the PutContent."""
        pc = PutContent(self.protocol, 'share', 'node', '', '',
                        0, 0, 0, StringIO(''), magic_hash='foo')
        pc.start()
        pc_msg = protocol_pb2.Message()
        data = self.protocol.transport.value()
        pc_msg.ParseFromString(data[request.SIZE_FMT_SIZE:])
        self.assertEqual(pc_msg.put_content.magic_hash, 'foo')

    def test_magic_hash_none(self):
        """Don't send magic hash in the PutContent."""
        pc = PutContent(self.protocol, 'share', 'node', '', '',
                        0, 0, 0, StringIO(''))
        pc.start()
        pc_msg = protocol_pb2.Message()
        data = self.protocol.transport.value()
        pc_msg.ParseFromString(data[request.SIZE_FMT_SIZE:])
        self.assertEqual(pc_msg.put_content.magic_hash, '')
