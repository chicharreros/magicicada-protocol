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

from unittest import TestCase
from io import BytesIO

from twisted.internet import defer, task
from twisted.trial.unittest import TestCase as TwistedTestCase

from magicicadaprotocol import client, protocol_pb2


class FakeRequest(object):
    """Fake Request class that is handy for tests."""

    def __init__(self):
        self.messages = []
        self.cancelled = False
        self.max_payload_size = 3  # lower limit, easier for testing

    def sendMessage(self, message):
        """Store the message in own list."""
        name = protocol_pb2.Message.DESCRIPTOR.enum_types_by_name[
            'MessageType'].values_by_number[message.type].name
        self.messages.append(name)


class TestProducingState(TestCase):
    """Test for filename validation and normalization."""

    def setUp(self):
        fh = BytesIO()
        fh.write(b"abcde")
        fh.seek(0)
        req = FakeRequest()
        self.bmp = client.BytesMessageProducer(req, fh, 0)

    def test_start(self):
        """It starts not producing anything."""
        self.assertFalse(self.bmp.producing)

    def test_resume_from_init(self):
        """Produce after a Resume coming from init."""
        self.bmp.resumeProducing()
        self.assertTrue(self.bmp.producing)

    def test_resume_from_pause(self):
        """Produce after a Resume coming from pause."""
        self.bmp.pauseProducing()
        self.bmp.resumeProducing()
        self.assertTrue(self.bmp.producing)

    def test_resume_from_stop(self):
        """Produce after a Resume coming from stop."""
        self.bmp.stopProducing()
        self.bmp.resumeProducing()
        self.assertTrue(self.bmp.producing)

    def test_resume_and_pause(self):
        """Pause after a Resume."""
        self.bmp.resumeProducing()
        self.bmp.pauseProducing()
        self.assertFalse(self.bmp.producing)

    def test_resume_and_stop(self):
        """Stop after a Resume."""
        self.bmp.resumeProducing()
        self.bmp.stopProducing()
        self.assertFalse(self.bmp.producing)


class TestGenerateData(TwistedTestCase):
    """Test for data generation."""

    timeout = 1

    @defer.inlineCallbacks
    def setUp(self):
        yield super(TestGenerateData, self).setUp()
        fh = BytesIO()
        fh.write(b"abcde")
        fh.seek(0)
        self.req = FakeRequest()
        self.clock = task.Clock()
        self.bmp = client.BytesMessageProducer(self.req, fh, 0)
        self.patch(self.bmp, 'callLater', self.clock.callLater)

    def test_start(self):
        """It starts not producing anything."""
        self.assertEqual(self.req.messages, [])

    def test_generate(self):
        """Generate all data after a resume."""
        self.bmp.resumeProducing()
        self.clock.advance(1)
        self.assertEqual(self.req.messages, ["BYTES", "BYTES", "EOF"])

    def test_no_double_EOF(self):
        """Don't send EOF after finished."""
        self.bmp.resumeProducing()
        self.clock.advance(1)
        self.assertEqual(self.req.messages, ["BYTES", "BYTES", "EOF"])
        self.req.messages[:] = []
        self.bmp.resumeProducing()
        self.clock.advance(1)
        self.assertEqual(self.req.messages, [])
