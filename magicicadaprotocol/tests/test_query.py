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

"""Tests for querying lots of items."""

import os
import unittest

from magicicadaprotocol.client import MultiQuery


class TestQuery10(unittest.TestCase):
    """Check that MultiQuery works using an iterator."""

    N = 10

    def test_query_many(self):
        """Check the lenght is right, there isn't much more to compare."""
        # larger than real ids and hashes, and also randomer than real, so we
        # can get away with creating less queries per Query
        a_id = str(os.urandom(1024))
        b_id = str(os.urandom(1024))
        a_hash = str(os.urandom(1024))
        items = [(a_id, b_id, a_hash) for _ in range(self.N)]
        multi_query_list = MultiQuery(None, items)
        multi_query_iter = MultiQuery(None, iter(items))
        self.assertEqual(len(multi_query_list.queries),
                         len(multi_query_iter.queries))


class TestQuery1000(TestQuery10):
    """Check with even more queries."""

    N = 1000
