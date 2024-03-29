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

"""Provides wrapper classes for delta nodes messages."""

from magicicadaprotocol import protocol_pb2

FILE = 0
DIRECTORY = 1

file_type_registry = {
    protocol_pb2.FileInfo.FILE: FILE,
    protocol_pb2.FileInfo.DIRECTORY: DIRECTORY,
}


class FileInfoDelta:
    """Hold the file/directory object information for a delta."""

    def __init__(
        self,
        generation,
        is_live,
        file_type,
        parent_id,
        share_id,
        node_id,
        name,
        is_public,
        content_hash,
        crc32,
        size,
        last_modified,
    ):
        self.generation = generation
        self.is_live = is_live
        self.file_type = file_type
        self.parent_id = parent_id
        self.share_id = share_id
        self.node_id = node_id
        self.name = name
        self.is_public = is_public
        self.content_hash = content_hash
        self.crc32 = crc32
        self.size = size
        self.last_modified = last_modified

    @classmethod
    def from_message(cls, delta_info):
        """Creates the object using the information from a message."""
        info = delta_info.file_info
        parent_id = None
        if info.parent:
            parent_id = info.parent
        result = cls(
            generation=delta_info.generation,
            is_live=delta_info.is_live,
            file_type=file_type_registry[info.type],
            parent_id=parent_id,
            share_id=info.share,
            node_id=info.node,
            name=info.name,
            is_public=info.is_public,
            content_hash=info.content_hash,
            crc32=info.crc32,
            size=info.size,
            last_modified=info.last_modified,
        )
        return result

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.__dict__ == other.__dict__


message_type_registry = {
    protocol_pb2.DeltaInfo.FILE_INFO: FileInfoDelta.from_message
}


def from_message(message):
    """Generates Info objects from DELTA_INFO messages."""
    return message_type_registry[message.delta_info.type](message.delta_info)
