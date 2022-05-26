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

"""Tests for generation node data type."""

import unittest

from magicicadaprotocol import (
    protocol_pb2,
    delta,
    content_hash,
    request,
)

SHARE = "share_id"
NODE = "node_id"
PARENT = "parent_id"
HASH = content_hash.content_hash_factory().content_hash()
CRC = 4096


def get_message():
    """Returns a DELTA_INFO message with sample data in the fields."""
    message = protocol_pb2.Message()
    message.type = protocol_pb2.Message.DELTA_INFO
    message.delta_info.type = protocol_pb2.DeltaInfo.FILE_INFO
    message.delta_info.generation = 10
    message.delta_info.is_live = False
    message.delta_info.file_info.type = protocol_pb2.FileInfo.FILE
    message.delta_info.file_info.name = "filename"
    message.delta_info.file_info.share = str(SHARE)
    message.delta_info.file_info.node = str(NODE)
    message.delta_info.file_info.parent = str(PARENT)
    message.delta_info.file_info.is_public = True
    message.delta_info.file_info.content_hash = HASH
    message.delta_info.file_info.crc32 = CRC
    message.delta_info.file_info.size = 1024
    message.delta_info.file_info.last_modified = 2048
    return message


class DeltaTestCase(unittest.TestCase):
    """Check Delta data type."""

    def test_correct_attributes(self):
        """Assert over attribute correctness."""
        m = delta.from_message(get_message())
        self.assertIsInstance(m, delta.FileInfoDelta)
        self.assertEqual(m.generation, 10)
        self.assertEqual(m.is_live, False)
        self.assertEqual(m.file_type, delta.FILE)
        self.assertEqual(m.name, "filename")
        self.assertEqual(m.share_id, SHARE)
        self.assertEqual(m.node_id, NODE)
        self.assertEqual(m.content_hash, HASH)
        self.assertEqual(m.crc32, CRC)
        self.assertEqual(m.size, 1024)
        self.assertEqual(m.last_modified, 2048)

    def test_is_equal(self):
        """Test object equality."""
        m = delta.from_message(get_message())
        m2 = delta.from_message(get_message())
        self.assertEqual(m, m2)

    def test_root_share_id(self):
        """Test that DeltaInfo.from_message works with request.ROOT."""
        msg = get_message()
        msg.delta_info.file_info.share = request.ROOT
        m = delta.from_message(msg)
        self.assertIsInstance(m, delta.FileInfoDelta)
        self.assertEqual(m.generation, 10)
        self.assertEqual(m.is_live, False)
        self.assertEqual(m.file_type, delta.FILE)
        self.assertEqual(m.name, "filename")
        self.assertEqual(m.share_id, request.ROOT)
        self.assertEqual(m.node_id, NODE)
        self.assertEqual(m.content_hash, HASH)
        self.assertEqual(m.crc32, CRC)
        self.assertEqual(m.size, 1024)
        self.assertEqual(m.last_modified, 2048)

    def test_parent_id_None(self):
        """Test that DeltaInfo correctly handle paren_id = ''."""
        msg = get_message()
        msg.delta_info.file_info.parent = ''
        m = delta.from_message(msg)
        self.assertEqual(m.parent_id, None)
