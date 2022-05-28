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

"""Tests for the protocol hashing methods."""

import hashlib
import os
import pickle
import unittest

from magicicadaprotocol.content_hash import (
    MagicContentHash,
    SHA1ContentHash,
    content_hash_factory,
    magic_hash_factory,
)


class FactoriesTest(unittest.TestCase):
    """Test the hasher factories."""

    def test_content_hash_factory(self):
        """Check the factory for the normal content hash."""
        o = content_hash_factory()
        self.assertIsInstance(o, SHA1ContentHash)

    def test_content_hash_method(self):
        """Test the method that the normal content hash uses."""
        self.assertEqual(SHA1ContentHash.method, hashlib.sha1)

    def test_content_hash_method_name(self):
        """Test the method name for the normal content hash."""
        self.assertEqual(SHA1ContentHash.method_name, 'sha1')

    def test_magic_hash_factory(self):
        """Check the factory for the magic content hash."""
        o = magic_hash_factory()
        self.assertIsInstance(o, MagicContentHash)

    def test_magic_hash_method(self):
        """Test the method that the magic content hash uses."""
        self.assertEqual(MagicContentHash.method, hashlib.sha1)

    def test_magic_hash_method_name(self):
        """Test the method name for the magic content hash."""
        self.assertEqual(MagicContentHash.method_name, 'magic_hash')


class ContentHashingTests(unittest.TestCase):
    """Test normal content hashing."""

    def setUp(self):
        """Set up."""
        self.hasher = SHA1ContentHash()

    def test_hashing_empty(self):
        """Test the hashing for no data."""
        r = self.hasher.hexdigest()
        s = hashlib.sha1().hexdigest()
        self.assertEqual(r, s)

    def test_hashing_content_once(self):
        """Test the hashing for some content sent once."""
        self.hasher.update(b"foobar")
        r = self.hasher.hexdigest()
        s = hashlib.sha1(b"foobar").hexdigest()
        self.assertEqual(r, s)

    def test_hashing_content_upadting(self):
        """Test the hashing for some content sent more than once."""
        c1 = os.urandom(1000)
        c2 = os.urandom(1000)
        self.hasher.update(c1)
        self.hasher.update(c2)
        r = self.hasher.hexdigest()
        s = hashlib.sha1(c1 + c2).hexdigest()
        self.assertEqual(r, s)

    def test_content_hash(self):
        """The hexdigest with the prefix."""
        self.hasher.update(b"foobar")
        hexdigest = self.hasher.hexdigest()
        ch = self.hasher.content_hash()
        self.assertEqual("sha1:" + hexdigest, ch)


class MagicHashingTests(unittest.TestCase):
    """Test magic content hashing."""

    def setUp(self):
        """Set up."""
        self.hasher = MagicContentHash()

    def test_hashing_empty(self):
        """Test the hashing for no data."""
        r = self.hasher.hash_object.hexdigest()
        s = hashlib.sha1(b"Ubuntu One").hexdigest()
        self.assertEqual(r, s)

    def test_hashing_content_once(self):
        """Test the hashing for some content sent once."""
        self.hasher.update(b"foobar")
        r = self.hasher.hash_object.hexdigest()
        s = hashlib.sha1(b"Ubuntu Onefoobar").hexdigest()
        self.assertEqual(r, s)

    def test_hashing_content_upadting(self):
        """Test the hashing for some content sent more than once."""
        c1 = os.urandom(1000)
        c2 = os.urandom(1000)
        self.hasher.update(c1)
        self.hasher.update(c2)
        r = self.hasher.hash_object.hexdigest()
        s = hashlib.sha1(b"Ubuntu One" + c1 + c2).hexdigest()
        self.assertEqual(r, s)

    def test_hexdigest_hiding(self):
        """Can not access the hex digest."""
        self.assertRaises(NotImplementedError, self.hasher.hexdigest)

    def test_digest_hiding(self):
        """Can not access the digest."""
        self.assertRaises(NotImplementedError, self.hasher.digest)

    def test_content_hash_hiding(self):
        """The content hash is not the content hash!"""
        self.hasher.update(b"foobar")
        hexdigest = self.hasher.hash_object.hexdigest()
        ch = self.hasher.content_hash()

        # not a string, and never show the content
        self.assertFalse(isinstance(ch, str))
        self.assertFalse(hexdigest in str(ch))
        self.assertFalse(hexdigest in repr(ch))

        # we have the real value hidden in the object
        self.assertEqual('magic_hash:' + hexdigest, ch._magic_hash)

    def test_not_pickable(self):
        """The magic hasher and value can not be pickled"""
        # the hasher
        self.assertRaises(NotImplementedError, pickle.dumps, self.hasher)

        # the value
        ch = self.hasher.content_hash()
        self.assertRaises(NotImplementedError, pickle.dumps, ch)
