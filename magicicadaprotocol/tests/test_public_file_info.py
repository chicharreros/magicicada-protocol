# -*- coding: utf-8 -*-
#
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

"""Tests for generation node data type."""

import unittest

from magicicadaprotocol import protocol_pb2, public_file_info, request

SHARE = "share_id"
NODE = "node_id"
PUBLIC_URL = "test public url"


def get_message():
    """Returns a PUBLIC_FILE_INFO message with sample data in the fields."""
    message = protocol_pb2.Message()
    message.type = protocol_pb2.Message.PUBLIC_FILE_INFO
    message.public_file_info.share = str(SHARE)
    message.public_file_info.node = str(NODE)
    message.public_file_info.is_public = True
    message.public_file_info.public_url = PUBLIC_URL
    return message


class DeltaTestCase(unittest.TestCase):
    """Check Delta data type."""

    def test_correct_attributes(self):
        """Assert over attribute correctness."""
        m = public_file_info.PublicFileInfo.from_message(get_message())
        self.assertEqual(m.share_id, SHARE)
        self.assertEqual(m.node_id, NODE)
        self.assertEqual(m.is_public, True)
        self.assertEqual(m.public_url, PUBLIC_URL)

    def test_is_equal(self):
        """Test object equality."""
        m = public_file_info.PublicFileInfo.from_message(get_message())
        m2 = public_file_info.PublicFileInfo.from_message(get_message())
        self.assertEqual(m, m2)

    def test_root_share_id(self):
        """Test that DeltaInfo.from_message works with request.ROOT."""
        msg = get_message()
        msg.public_file_info.share = request.ROOT
        m = public_file_info.PublicFileInfo.from_message(msg)
        self.assertEqual(m.share_id, request.ROOT)
