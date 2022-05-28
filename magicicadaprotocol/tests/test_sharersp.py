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

"""Tests for shares response."""

import uuid

from twisted.internet import defer
from twisted.trial.unittest import TestCase

from magicicadaprotocol import protocol_pb2
from magicicadaprotocol.sharersp import ShareResponse


class ShareResponseFromParamsTest(TestCase):
    """Tests ShareResponse.from_params."""

    access_level = 'View'

    def assertShareResponse(self, share, args):
        """Check share against args."""
        self.assertEqual(ShareResponse, type(share))
        self.assertEqual(args[0], share.id)
        self.assertEqual(args[1], share.direction)
        self.assertEqual(args[2], share.subtree)
        self.assertEqual(args[3], share.name)
        self.assertEqual(args[4], share.other_username)
        self.assertEqual(args[5], share.other_visible_name)
        self.assertEqual(args[6], share.accepted)
        self.assertEqual(args[7], share.access_level)
        if share.direction == "from_me":
            if len(args) == 9:
                self.assertEqual(args[8], share.subtree_volume_id)
            else:
                self.assertEqual(None, share.subtree_volume_id)
        else:
            self.assertFalse(hasattr(share, 'subtree_volume_id'))

    def test_to_me(self):
        """Test ShareResponse.from_params with a 'to_me' share."""
        args = (uuid.uuid4(), "to_me", uuid.uuid4(), "share_name", "username",
                "visible_name", True, self.access_level)
        share = ShareResponse.from_params(*args)
        self.assertShareResponse(share, args)

    def test_to_me_with_volume(self):
        """Test ShareResponse.from_params with a 'to_me' share."""
        args = (uuid.uuid4(), "to_me", uuid.uuid4(), "share_name", "username",
                "visible_name", True, self.access_level, uuid.uuid4())
        self.assertRaises(ValueError, ShareResponse.from_params, *args)

    def test_from_me(self):
        """Test ShareResponse.from_params with a 'from_me' share."""
        args = (uuid.uuid4(), "from_me", uuid.uuid4(), "share_name",
                "username", "visible_name", True, self.access_level,
                uuid.uuid4())
        share = ShareResponse.from_params(*args)
        self.assertShareResponse(share, args)

    def test_from_me_without_volume(self):
        """Test ShareResponse.from_params with a 'from_me' share."""
        args = (uuid.uuid4(), "from_me", uuid.uuid4(), "share_name",
                "username", "visible_name", True, self.access_level)
        share = ShareResponse.from_params(*args)
        self.assertShareResponse(share, args)


class ShareResponseFromParamsModifyTest(ShareResponseFromParamsTest):
    """Tests ShareResponse.from_params with 'Modify' access_level."""

    access_level = "Modify"


class ShareResponseFromToMsgTest(TestCase):
    """Tests ShareResponse.load_from_msg and dump_to_msg."""

    access_level = 'View'

    @defer.inlineCallbacks
    def setUp(self):
        yield super(ShareResponseFromToMsgTest, self).setUp()
        self.msg = protocol_pb2.Message()
        self.msg.type = protocol_pb2.Message.SHARES_INFO

    def assertEqualShare(self, share, other):
        """Check if two shares are equal."""
        self.assertEqual(vars(share), vars(other))

    def test_to_me(self):
        """Test ShareResponse.from_params with a 'to_me' share."""
        args = (uuid.uuid4(), "to_me", uuid.uuid4(), "share_name", "username",
                "visible_name", True, self.access_level)
        share = ShareResponse.from_params(*args)
        share.dump_to_msg(self.msg.shares)
        self.assertEqualShare(share,
                              ShareResponse.load_from_msg(self.msg.shares))

    def test_to_me_with_volume(self):
        """Test ShareResponse.from_params with a 'to_me' share."""
        args = (uuid.uuid4(), "to_me", uuid.uuid4(), "share_name", "username",
                "visible_name", True, self.access_level)
        share = ShareResponse.from_params(*args)
        share.dump_to_msg(self.msg.shares)
        self.msg.shares.subtree_volume_id = str(uuid.uuid4())
        self.assertEqualShare(share,
                              ShareResponse.load_from_msg(self.msg.shares))

    def test_from_me(self):
        """Test ShareResponse.from_params with a 'from_me' share."""
        args = (uuid.uuid4(), "from_me", uuid.uuid4(), "share_name",
                "username", "visible_name", True, self.access_level,
                uuid.uuid4())
        share = ShareResponse.from_params(*args)
        share.dump_to_msg(self.msg.shares)
        self.assertEqualShare(share,
                              ShareResponse.load_from_msg(self.msg.shares))

    def test_from_me_without_volume(self):
        """Test ShareResponse.from_params with a 'from_me' share."""
        args = (uuid.uuid4(), "from_me", uuid.uuid4(), "share_name",
                "username", "visible_name", True, self.access_level)
        share = ShareResponse.from_params(*args)
        share.dump_to_msg(self.msg.shares)
        self.assertEqualShare(share,
                              ShareResponse.load_from_msg(self.msg.shares))


class ShareResponseFromToMsgModifyTest(ShareResponseFromToMsgTest):
    """Tests ShareResponse.load_from_msg and dump_to_msg with 'Modify'."""

    access_level = 'Modify'
