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

"""Message validation."""

import re
from uuid import UUID

from google.protobuf.message import Message as _PBMessage
from google.protobuf.internal.containers import BaseContainer as _PBContainer
try:
    from google.protobuf.internal.cpp_message import RepeatedCompositeContainer
except ImportError:
    CONTAINER_CLASSES = _PBContainer
else:
    CONTAINER_CLASSES = (_PBContainer, RepeatedCompositeContainer)


def is_valid_node(node_id):
    """
    A node id is a hex UUID.
    """
    try:
        return str(UUID(node_id)) == node_id
    except Exception:
        return False


def is_valid_crc32(crc32):
    """
    Valid CRC32s are nonnegative integers
    """
    return int(crc32) >= 0


def is_valid_share(share_id):
    """
    A share id is either the empty string, or a node id.
    """
    return share_id == '' or is_valid_node(share_id)


def is_valid_sha1(sha1):
    """Validate 'sha1'.

    A valid sha1 hash reads "sha1:", and then a 40 hex characters.

    """
    return bool(re.match(r'sha1:[0-9a-z]{40}$', sha1))


def is_valid_hash(a_hash):
    """Validate 'a_hash'.

    A valid hash is either the empty string, request.UNKNOWN_HASH, or one of
    the other known hash types.

    """
    # circular import
    from magicicadaprotocol import request
    is_valid = (a_hash == '' or a_hash == request.UNKNOWN_HASH or
                is_valid_sha1(a_hash))
    return is_valid


def validate_message(message):
    """
    Recursively validate a message's fields
    """
    is_invalid = []
    from magicicadaprotocol import validators  # this is us!
    for descriptor, submsg in message.ListFields():
        if isinstance(submsg, CONTAINER_CLASSES):
            # containers are iterables that have messages in them
            for i in submsg:
                is_invalid.extend(validate_message(i))
        elif isinstance(submsg, _PBMessage):
            # a plain sub-message
            is_invalid.extend(validate_message(submsg))
        else:
            # we got down to the actual fields! yay
            validator = getattr(validators,
                                "is_valid_" + descriptor.name, None)
            if validator is not None:
                if not validator(submsg):
                    is_invalid.append("Invalid %s: %r"
                                      % (descriptor.name, submsg))
    return is_invalid


is_valid_parent_node = is_valid_node
is_valid_new_parent_node = is_valid_node
is_valid_subtree = is_valid_node
is_valid_share_id = is_valid_share
