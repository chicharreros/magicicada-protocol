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

"""Tests for GetContent request."""

import unittest

from twisted.test.proto_helpers import StringTransport

from magicicadaprotocol import protocol_pb2
from magicicadaprotocol.client import GetContent, StorageClient


class ProcessMessageTestCase(unittest.TestCase):
    """Tests for message processing."""

    def make_protocol(self):
        protocol = StorageClient()
        protocol.transport = StringTransport()
        return protocol

    def test_handles_EOF(self):
        gc = GetContent(
            protocol=self.make_protocol(),
            share='share',
            node_id='node_id',
            a_hash='sha1:hash',
            offset=0,
            callback=None,
        )
        gc.start()
        gc.parts = [b'foo', b'bar']

        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.EOF
        gc.processMessage(message)

        self.assertEqual(gc.data, b'foobar')
