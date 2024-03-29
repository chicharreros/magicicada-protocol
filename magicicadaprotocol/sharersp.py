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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""A handy class to use Shares."""

import uuid

from magicicadaprotocol import volumes


class ShareResponse:
    """This is a handy object to support all the fields of a share listing."""

    @classmethod
    def from_params(
        cls,
        share_id,
        direction,
        subtree,
        share_name,
        other_username,
        other_visible_name,
        accepted,
        access_level,
        subtree_volume_id=None,
    ):
        """Creates the object from given parameters."""
        o = cls()
        o.id = share_id
        o.direction = direction
        o.subtree = subtree
        o.name = share_name
        o.other_username = other_username
        o.other_visible_name = other_visible_name
        o.accepted = accepted
        o.access_level = access_level
        if direction == "to_me" and subtree_volume_id is not None:
            raise ValueError(
                "Shares with direction 'to_me' must not have" " a volume_id"
            )
        elif direction == "from_me":
            o.subtree_volume_id = subtree_volume_id
        return o

    @classmethod
    def load_from_msg(cls, msg):
        """Creates the object loading the information from a message."""
        o = cls()
        o.id = uuid.UUID(msg.share_id)
        o.direction = volumes._direction_prot2nice[msg.direction]
        o.subtree = uuid.UUID(msg.subtree)
        o.name = msg.share_name
        o.other_username = msg.other_username
        o.other_visible_name = msg.other_visible_name
        o.accepted = msg.accepted
        o.access_level = volumes._access_prot2nice[msg.access_level]
        if o.direction == "from_me":
            if msg.subtree_volume_id:
                o.subtree_volume_id = uuid.UUID(msg.subtree_volume_id)
            else:
                o.subtree_volume_id = None
        return o

    def dump_to_msg(self, msg):
        """Dumps the object information to a given message."""
        msg.share_id = str(self.id)
        msg.direction = volumes._direction_nice2prot[self.direction]
        msg.subtree = str(self.subtree)
        msg.share_name = self.name
        msg.other_username = self.other_username
        msg.other_visible_name = self.other_visible_name
        msg.accepted = self.accepted
        msg.access_level = volumes._access_nice2prot[self.access_level]
        if self.direction == "from_me":
            if self.subtree_volume_id:
                msg.subtree_volume_id = str(self.subtree_volume_id)

    def __str__(self):
        t = "Share %r [%s] (other: %s, access: %s, accepted: %s, id: %s)" % (
            self.name,
            self.direction,
            self.other_username,
            self.access_level,
            self.accepted,
            self.id,
        )
        return t


class NotifyShareHolder:
    """This is a handy object to support all the fields of a share notify."""

    @classmethod
    def from_params(
        cls,
        share_id,
        subtree,
        share_name,
        from_username,
        from_visible_name,
        access_level,
    ):
        """Creates the object from given parameters."""
        o = cls()
        o.share_id = share_id
        o.subtree = subtree
        o.share_name = share_name
        o.from_username = from_username
        o.from_visible_name = from_visible_name
        o.access_level = access_level
        return o

    @classmethod
    def load_from_msg(cls, msg):
        """Creates the object loading the information from a message."""
        o = cls()
        o.share_id = uuid.UUID(msg.share_id)
        o.subtree = msg.subtree
        o.share_name = msg.share_name
        o.from_username = msg.from_username
        o.from_visible_name = msg.from_visible_name
        o.access_level = volumes._access_prot2nice[msg.access_level]
        return o

    def dump_to_msg(self, msg):
        """Dumps the object information to a given message."""
        msg.share_id = str(self.share_id)
        msg.subtree = str(self.subtree)
        msg.share_name = self.share_name
        msg.from_username = self.from_username
        msg.from_visible_name = self.from_visible_name
        msg.access_level = volumes._access_nice2prot[self.access_level]

    def __str__(self):
        t = "Share Notification %r (from: %s, access: %s, id: %s)" % (
            self.share_name,
            self.from_username,
            self.access_level,
            self.share_id,
        )
        return t
