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

"""Tests for directory content serialization/unserialization."""

from io import BytesIO
from unittest import TestCase

from magicicadaprotocol.dircontent import (
    parse_dir_content, write_dir_content, DirEntry,
    normalize_filename, validate_filename, InvalidFilename)
from magicicadaprotocol.dircontent_pb2 import DIRECTORY, FILE


class TestFilenames(TestCase):
    """Tests for filename validation and normalization."""
    def test_trivial(self):
        """Tests the trivial case of an ASCII filename."""
        self.assertEqual('foobar', normalize_filename('foobar'))
        validate_filename('foobar')

    def test_special_entries(self):
        """Tests that special directory entries aren't allowed."""
        self.assertRaises(InvalidFilename, normalize_filename, ".")
        self.assertRaises(InvalidFilename, validate_filename, ".")
        self.assertRaises(InvalidFilename, normalize_filename, "..")
        self.assertRaises(InvalidFilename, validate_filename, "..")

    def test_valid_characters(self):
        """Tests that all weird but valid characters are accepted."""
        for n in range(1, 32):
            filename = "xy" + chr(n) + "zzy"
            normalize_filename(filename)
            validate_filename(filename)
        for c in [':', ';', '*', '?', '\\', '\x7f']:
            filename = "xy" + c + "zzy"
            normalize_filename(filename)
            validate_filename(filename)

    def test_excluded_character(self):
        """Tests that all excluded characters are banned."""
        for c in ['/', chr(0)]:
            name = "xy" + c + "zzy"
            try:
                self.assertRaises(InvalidFilename, normalize_filename, name)
                self.assertRaises(InvalidFilename, validate_filename, name)
            except AssertionError as e:
                raise AssertionError("%s for %s" % (e, name))


class TestDirContent(TestCase):
    """Tests for Directory content serialization/unserialization."""

    def testDirEntryEquality(self):
        """Verify that DirEntry equality tests work."""
        a = DirEntry(name="a", node_type=FILE, uuid="some-id")
        a2 = DirEntry(name="a", node_type=FILE, uuid="some-id")
        b = DirEntry(name="b", node_type=FILE, uuid="other-id")
        self.assertEqual(a, a)
        self.assertEqual(a, a2)
        self.assertNotEqual(a, b)
        self.assertIsNotNone(a)

    def testEntryName(self):
        """Verify that name and utf8_name are encoded and decoded properly."""
        unicode_name = "\u269b"
        utf8_name = unicode_name.encode('utf8')  # b"\xE2\x9A\x9B"
        a = DirEntry(name=unicode_name)
        b = DirEntry(utf8_name=utf8_name)
        for entry in [a, b]:
            self.assertEqual(entry.name, unicode_name)
            self.assertEqual(entry.utf8_name, utf8_name)
            self.assertIsInstance(entry.name, str)
            self.assertIsInstance(entry.utf8_name, bytes)

    def testRoundtrip(self):
        """Verify that directory entries roundtrip successfully

        And in correct (sorted) order.

        """
        a = DirEntry(name="negatory", node_type=FILE, uuid="abcd")
        b = DirEntry(name="beef", node_type=DIRECTORY, uuid="efgh")
        buf = BytesIO()
        write_dir_content([a, b], buf)
        buf.seek(0, 0)
        output_entries = [e for e in parse_dir_content(buf)]
        self.assertEqual(output_entries, [b, a])
