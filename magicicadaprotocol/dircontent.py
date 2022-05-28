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

"""Standard routines for working with directory content."""

import operator
import re

from magicicadaprotocol.dircontent_pb2 import DirectoryContent

ILLEGAL_FILENAMES = [".", ".."]
ILLEGAL_FILENAME_CHARS_RE_SOURCE = r'[\000/]'
ILLEGAL_FILENAME_CHARS_RE = re.compile(ILLEGAL_FILENAME_CHARS_RE_SOURCE)


class InvalidFilename(Exception):
    """Raised when a filename is invalid."""


def validate_filename(filename):
    """Validate a filename for use with the storage service.

    Raises InvalidFilename if the filename is invalid.

    """
    if type(filename) != str:
        raise InvalidFilename("Filename is not unicode")
    if filename in ILLEGAL_FILENAMES:
        raise InvalidFilename("%s is a reserved filename" % (filename,))
    if ILLEGAL_FILENAME_CHARS_RE.search(filename) is not None:
        raise InvalidFilename("%s contains illegal characters" % (filename,))


def normalize_filename(filename):
    """Take a filename and return the normalized form.

    Raise InvalidFilename if the filename is invalid for use with the storage
    service.

    """
    validate_filename(filename)
    return filename


def parse_dir_content(stream):
    """Unserialize directory content from a stream.

    @param stream: an IO-alike stream object
    @return: a generator yielding DirEntry objects

    """
    raw_content = stream.read()
    unserialized_content = DirectoryContent()
    # XXX what exceptions can protobuf's parser raise?
    unserialized_content.ParseFromString(raw_content)

    for entry in unserialized_content.entries:
        yield DirEntry(name=entry.name, node_type=entry.node_type,
                       uuid=entry.node)


def write_dir_content(entries, stream):
    """Takes a sequence of DirEntry objects, sorts them, and writes
    the corresponding serialized directory content to the given stream.

    @param entries: an iterator producing DirEntry objects
    @param stream: an IO-compatible stream to write to

    """
    sorted_entries = sorted(entries, key=operator.attrgetter('utf8_name'))
    for chunk in yield_presorted_dir_content(sorted_entries):
        stream.write(chunk)


def yield_presorted_dir_content(sorted_entries):
    """Takes a presorted sequence of DirEntry objects and yields each
    chunks of serialized content.

    @param sorted_entries: a presorted sequence of DirEntry objects

    """

    # A series of concatenated DirectoryContent objects is equivalent to
    # a single DirectoryContent object with fields repeated.  Among other
    # things, this makes it easy to re-use the same protobuf objects for
    # each entry that we serialize.
    content = DirectoryContent()
    pb_entry = content.entries.add()

    for entry in sorted_entries:
        pb_entry.name = entry.name
        pb_entry.node_type = entry.node_type
        pb_entry.node = entry.uuid
        yield content.SerializeToString()


class DirEntry:
    """An object representing a directory entry.

    name: the node's name in the directory as a string
    utf8_name: the node's name encoded in UTF-8
    node_type: the node's type (one of FILE, DIRECTORY, or SYMLINK)
    uuid: the node's server-side UUID

    """

    def __init__(self, name=None, utf8_name=None, node_type=None, uuid=None):
        """Initializes a directory entry object.  Providing either the unicode
        or UTF-8 names will result in both name fields being set.

        @param name: the node's name in the directory
        @param utf8_name: the node's name encoded in UTF-8
        @param node_type: the node's type
        @param uuid: the node's server-sude UUID

        """
        if name is not None:
            self.name = name
        elif utf8_name is not None:
            self.name = utf8_name.decode("utf-8")
        else:
            self.name = None

        if utf8_name is not None:
            self.utf8_name = utf8_name
        elif name is not None:
            self.utf8_name = name.encode("utf-8")
        else:
            self.utf8_name = None

        self.node_type = node_type
        self.uuid = uuid

    def __eq__(self, other):
        if isinstance(other, DirEntry):
            return self.name == other.name and \
                self.utf8_name == other.utf8_name and \
                self.node_type == other.node_type and \
                self.uuid == other.uuid
        else:
            return False
