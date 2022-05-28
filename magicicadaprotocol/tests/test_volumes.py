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

"""Tests for volume data type."""

import unittest
import uuid

from copy import copy

from magicicadaprotocol import protocol_pb2, volumes

PATH = '~/Documents/pdfs/moño/'
NAME = 'What a beatiful volume'
VOLUME = uuid.UUID('12345678-1234-1234-1234-123456789abc')
NODE = uuid.UUID('FEDCBA98-7654-3211-2345-6789ABCDEF12')
USER = 'dude'
FREE_BYTES = 1024
GENERATION = 999


class VolumeTestCase(unittest.TestCase):
    """Check Volume data type."""

    volume_id = VOLUME

    volume_class = volumes.Volume
    kwargs = dict(volume_id=VOLUME, node_id=NODE,
                  free_bytes=FREE_BYTES, generation=GENERATION)

    def setUp(self):
        """Initialize testing volume."""
        self.volume = self.volume_class(**self.kwargs)

    def tearDown(self):
        """Clean up."""
        self.volume = None

    def assert_correct_attributes(self):
        """Assert over attribute correctness."""
        self.assertEqual(self.volume_id, self.volume.volume_id)
        self.assertEqual(NODE, self.volume.node_id)
        self.assertEqual(FREE_BYTES, self.volume.free_bytes)
        self.assertEqual(GENERATION, self.volume.generation)

    def test_creation(self):
        """Test creation."""
        self.assert_correct_attributes()

    def test_is_a_volume(self):
        """Test class inheritance."""
        self.assertIsInstance(self.volume, volumes.Volume)

    def test_from_params(self):
        """Test creation using from_params."""
        self.volume = self.volume_class.from_params(**self.kwargs)
        self.assert_correct_attributes()

    def test_from_msg(self):
        """Test creation using from_msg."""
        self.assertRaises(NotImplementedError,
                          self.volume_class.from_msg, None)

    def test_is_equal(self):
        """Test object equality."""
        other = copy(self.volume)
        self.assertEqual(other, self.volume)

        for attr, value in self.kwargs.items():
            setattr(other, attr, None)
            self.assertNotEqual(
                other, self.volume, 'not equal when %s differ' % attr)
            setattr(other, attr, value)

        self.assertEqual(other, self.volume)


class ShareTestCase(VolumeTestCase):
    """Check Share data type."""

    to_me = volumes._direction_prot2nice[protocol_pb2.Shares.TO_ME]
    only_view = volumes._access_prot2nice[protocol_pb2.Shares.VIEW]

    volume_class = volumes.ShareVolume
    kwargs = dict(volume_id=VOLUME, node_id=NODE,
                  free_bytes=FREE_BYTES, generation=GENERATION,
                  direction=to_me,
                  share_name=NAME, other_username=USER,
                  other_visible_name=USER, accepted=False,
                  access_level=only_view)

    def assert_correct_attributes(self):
        """Assert over attribute correctness."""
        super(ShareTestCase, self).assert_correct_attributes()
        self.assertEqual(self.to_me, self.volume.direction)
        self.assertEqual(NAME, self.volume.share_name)
        self.assertEqual(USER, self.volume.other_username)
        self.assertEqual(USER, self.volume.other_visible_name)
        self.assertEqual(False, self.volume.accepted)
        self.assertEqual(self.only_view, self.volume.access_level)

    def test_from_msg(self):
        """Test creation using from_msg."""
        message = protocol_pb2.Shares()
        message.share_id = str(VOLUME).encode('utf8')
        message.subtree = str(NODE).encode('utf8')
        message.generation = GENERATION
        message.free_bytes = FREE_BYTES
        message.share_name = NAME
        message.other_username = USER
        message.other_visible_name = USER
        self.volume = self.volume_class.from_msg(message)
        self.assert_correct_attributes()


class UDFTestCase(VolumeTestCase):
    """Check UDF data type."""

    volume_class = volumes.UDFVolume
    kwargs = dict(volume_id=VOLUME, node_id=NODE,
                  free_bytes=FREE_BYTES, generation=GENERATION,
                  suggested_path=PATH)

    def assert_correct_attributes(self):
        """Assert over attribute correctness."""
        super(UDFTestCase, self).assert_correct_attributes()
        self.assertEqual(PATH, self.volume.suggested_path)

    def test_from_msg(self):
        """Test creation using from_msg."""
        message = protocol_pb2.UDFs()
        message.volume = str(VOLUME).encode('utf8')
        message.node = str(NODE).encode('utf8')
        message.suggested_path = PATH
        message.generation = GENERATION
        message.free_bytes = FREE_BYTES
        self.volume = self.volume_class.from_msg(message)
        self.assert_correct_attributes()


class RootTestCase(VolumeTestCase):
    """Check Root data type."""

    volume_id = None
    volume_class = volumes.RootVolume
    kwargs = dict(node_id=NODE, free_bytes=FREE_BYTES, generation=GENERATION)

    def test_from_msg(self):
        """Test creation using from_msg."""
        message = protocol_pb2.Root()
        message.node = str(NODE)
        message.generation = GENERATION
        message.free_bytes = FREE_BYTES
        self.volume = self.volume_class.from_msg(message)
        self.assert_correct_attributes()
