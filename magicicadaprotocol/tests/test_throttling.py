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

from twisted.internet import defer, task
from twisted.trial.unittest import TestCase as TwistedTestCase

from magicicadaprotocol import client


class FakeClient(object):
    """Fake a Client class that is handy for tests."""

    def __init__(self):
        self.events = []

    def throttleReads(self):
        """Store a throttleReads event."""
        self.events.append("thR")

    def unthrottleReads(self):
        """Store a unthrottleReads event."""
        self.events.append("unthR")

    def throttleWrites(self):
        """Store a throttleWrites event."""
        self.events.append("thW")

    def unthrottleWrites(self):
        """Store a unthrottleWrites event."""
        self.events.append("unthW")


class BaseThrottlingTestCase(TwistedTestCase):
    """Base test case for ThrottlingStorageClientFactory."""

    @defer.inlineCallbacks
    def setUp(self):
        yield super(BaseThrottlingTestCase, self).setUp()
        self.client = FakeClient()
        self.factories = []
        self.clock = task.Clock()
        self.patch(client.ThrottlingStorageClientFactory, 'callLater',
                   self.clock.callLater)

    def create_factory(self, enabled, read_limit, write_limit):
        """Create a ThrottlingStorageClientFactory with the specified args."""
        tscf = client.ThrottlingStorageClientFactory(enabled, read_limit,
                                                     write_limit)
        tscf.client = self.client
        self.factories.append(tscf)
        self.addCleanup(self.destroy_factory, tscf)
        return tscf

    def destroy_factory(self, factory):
        """Turn off a factory and delete it form self.factories."""
        del self.factories[self.factories.index(factory)]
        factory.unregisterProtocol(None)


class TestProducingState(BaseThrottlingTestCase):
    """Tests for 'producing' state with different limit values."""

    @defer.inlineCallbacks
    def setUp(self):
        yield super(TestProducingState, self).setUp()
        self.tscf = self.create_factory(True, 3, 3)

    def test_under_write_limit(self):
        """Don't pas the write limit, no event."""
        self.tscf.registerWritten(2)
        self.clock.advance(.1)
        self.assertEqual(self.client.events, [])

    def test_under_read_limit(self):
        """Don't pas the read limit, no event."""
        self.tscf.registerRead(2)
        self.clock.advance(.1)
        self.assertEqual(self.client.events, [])

    def test_above_write_throttles(self):
        """Above the write limit, throttles."""
        self.tscf.registerWritten(4)
        self.clock.advance(.1)
        self.assertEqual(self.client.events, ["thW"])

    def test_above_read_throttles(self):
        """Above the read limit, throttles."""
        self.tscf.registerRead(4)
        self.clock.advance(.1)
        self.assertEqual(self.client.events, ["thR"])

    def test_above_write_throttles_unthrottles(self):
        """Above the write limit, throttles and unthrottles after 1s."""
        self.tscf.registerWritten(4)
        self.clock.advance(1.1)
        self.assertEqual(self.client.events, ["thW", "unthW"])

    def test_above_read_throttles_unthrottles(self):
        """Above the read limit, throttles and unthrottles after 1s."""
        self.tscf.registerRead(4)
        self.clock.advance(1.1)
        self.assertEqual(self.client.events, ["thR", "unthR"])

    def test_very_above_write_throttles_unthrottles(self):
        """A lot above the write limit, throttles and unthrottles."""
        self.tscf.registerWritten(8)
        self.clock.advance(1.1)
        self.assertEqual(self.client.events, ["thW"])
        self.clock.advance(1)
        self.assertEqual(self.client.events, ["thW", "unthW"])

    def test_very_above_read_throttles_unthrottles(self):
        """A lot above the read limit, throttles and unthrottles."""
        self.tscf.registerRead(8)
        self.clock.advance(1.1)
        self.assertEqual(self.client.events, ["thR"])
        self.clock.advance(1)
        self.assertEqual(self.client.events, ["thR", "unthR"])

    def test_double_write(self):
        """Two writes on a row while throttling."""
        self.tscf.registerWritten(4)
        self.clock.advance(.1)
        self.assertEqual(self.client.events, ["thW"])
        self.tscf.registerWritten(1)
        self.clock.advance(2)
        self.assertEqual(self.client.events, ["thW", "unthW"])

    def test_double_read(self):
        """Two read on a row while throttling."""
        self.tscf.registerRead(4)
        self.clock.advance(.1)
        self.assertEqual(self.client.events, ["thR"])
        self.tscf.registerWritten(1)
        self.clock.advance(2)
        self.assertEqual(self.client.events, ["thR", "unthR"])


class TestLimitValuesInitialization(BaseThrottlingTestCase):
    """Test read/write limit values."""

    def _test_inactive_limits(self, read_limit, write_limit):
        """Test read_limit and write_limit with throttling enabled."""
        def check(tscf):
            """Check that there is no delayed calls nor events."""
            self.assertEqual(2, len(self.clock.getDelayedCalls()))
            self.assertNotEqual(None, tscf.resetReadThisSecondID)
            self.assertEqual(None, tscf.unthrottleReadsID)
            self.assertNotEqual(None, tscf.resetWriteThisSecondID)
            self.assertEqual(None, tscf.unthrottleWritesID)
            self.assertEqual(self.client.events, [])
        tscf = self.create_factory(True, read_limit, write_limit)
        check(tscf)
        self.clock.advance(1.1)
        check(tscf)

    def test_both_None(self):
        """Test for both limits None."""
        self._test_inactive_limits(None, None)

    def test_limits_0(self):
        """Test for both limits 0."""
        self.assertRaises(ValueError, self._test_inactive_limits, 0, 0)
        self.assertRaises(ValueError, self._test_inactive_limits, 1, 0)
        self.assertRaises(ValueError, self._test_inactive_limits, 0, 1)

    def test_both_negative(self):
        """Test for both limits -1."""
        self.assertRaises(ValueError, self._test_inactive_limits, -1, -1)

    def test_read_2_write_None(self):
        """Test "off" writeLimit value and throttling enabled."""
        tscf = self.create_factory(True, 2, None)
        # check that resetReadThisSecondID is running
        self.assertEqual(2, len(self.clock.getDelayedCalls()))
        self.assertNotEqual(None, tscf.resetReadThisSecondID)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.assertNotEqual(None, tscf.resetWriteThisSecondID)
        self.assertEqual(None, tscf.unthrottleWritesID)
        tscf.registerRead(4)
        self.clock.advance(0.5)
        self.assertEqual(self.client.events, ["thR"])
        self.assertNotEqual(None, tscf.resetReadThisSecondID)
        self.assertNotEqual(None, tscf.unthrottleReadsID)

    def test_read_None_write_2(self):
        """Test "off" readLimit value and throttling enabled."""
        tscf = self.create_factory(True, None, 2)
        # check that resetWriteThisSecondID is running
        self.assertEqual(2, len(self.clock.getDelayedCalls()))
        self.assertNotEqual(None, tscf.resetReadThisSecondID)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.assertNotEqual(None, tscf.resetWriteThisSecondID)
        self.assertEqual(None, tscf.unthrottleWritesID)
        tscf.registerWritten(4)
        self.clock.advance(0.5)
        self.assertEqual(self.client.events, ["thW"])
        self.assertNotEqual(None, tscf.resetWriteThisSecondID)
        self.assertNotEqual(None, tscf.unthrottleWritesID)

    def test_change_to_inavlid(self):
        """Test setting invalid limit values after initialization."""
        tscf = self.create_factory(True, 2, 2)
        self.assertRaises(ValueError, tscf._set_read_limit, -1)
        self.assertRaises(ValueError, tscf._set_write_limit, -1)


class TestResetLoops(BaseThrottlingTestCase):
    """Test the read/writeThisSecond reset loops."""

    def test_read_this_second_loop(self):
        """Test the reset loop for reads"""
        tscf = self.create_factory(True, 4, 4)
        tscf.registerRead(4)
        self.assertEqual(4, tscf.readThisSecond)
        self.clock.advance(1)
        self.assertEqual(0, tscf.readThisSecond)

    def test_write_this_second_loop(self):
        """Test the reset loop for writes"""
        tscf = self.create_factory(True, 4, 4)
        tscf.registerWritten(4)
        self.assertEqual(4, tscf.writtenThisSecond)
        self.clock.advance(1)
        self.assertEqual(0, tscf.writtenThisSecond)


class TestCheckBandwidth(BaseThrottlingTestCase):
    """Test the check[Read|Write]Bandwidth methods."""

    def _test_with_limits(self, read, write):
        """Test the check[Read|Wrte]Bandwidth using read and write limits."""
        tscf = self.create_factory(True, read, write)
        tscf.registerRead(4)
        tscf.registerWritten(4)
        self.assertEqual(4, tscf.readThisSecond)
        self.assertEqual(4, tscf.writtenThisSecond)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.clock.advance(1)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.assertEqual(None, tscf.unthrottleWritesID)
        self.assertEqual(0, tscf.readThisSecond)
        self.assertEqual(0, tscf.writtenThisSecond)

    def test_limits_0(self):
        """Test the check[Read|Wrte]Bandwidth with both = 0."""
        self.assertRaises(ValueError, self._test_with_limits, 0, 0)
        self.assertRaises(ValueError, self._test_with_limits, 1, 0)
        self.assertRaises(ValueError, self._test_with_limits, 0, 1)

    def test_limits_None(self):
        """Test the check[Read|Wrte]Bandwidth with both = None."""
        self._test_with_limits(None, None)

    def test_positive_limits(self):
        """Test the check[Read|Wrte]Bandwidth with both > 0."""
        tscf = self.create_factory(True, 2, 2)
        tscf.registerRead(4)
        tscf.registerWritten(4)
        self.assertEqual(4, tscf.readThisSecond)
        self.assertEqual(4, tscf.writtenThisSecond)
        self.assertNotEqual(None, tscf.unthrottleReadsID)
        self.assertNotEqual(None, tscf.unthrottleReadsID)
        self.clock.advance(.9)
        self.assertNotEqual(None, tscf.unthrottleReadsID)
        self.assertNotEqual(None, tscf.unthrottleReadsID)
        self.clock.advance(.1)
        self.assertEqual(0, tscf.readThisSecond)
        self.assertEqual(0, tscf.writtenThisSecond)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.assertEqual(None, tscf.unthrottleWritesID)


class TestThrottlingLimits(BaseThrottlingTestCase):
    """Test read/write limit behaviour and changes in runtime."""

    def test_limit_None_then_gt_0(self):
        """Test both None and change it to > 0."""
        def check(tscf, events=None, delayed_calls=2):
            """Check that there is no delayed calls nor events."""
            self.assertEqual(delayed_calls, len(self.clock.getDelayedCalls()))
            self.assertEqual(self.client.events, events or [])
        tscf = self.create_factory(True, None, None)
        self.clock.advance(1.1)
        check(tscf)
        tscf.readLimit = 2
        tscf.writeLimit = 2
        tscf.registerRead(4)
        tscf.registerWritten(4)
        self.clock.advance(0.9)
        expected_events = ['thR', 'thW']
        check(tscf, delayed_calls=4, events=expected_events)
        self.clock.advance(1)
        expected_events += ['unthR', 'unthW']
        check(tscf, events=expected_events)
        self.clock.advance(1.1)
        check(tscf, events=expected_events)
        tscf.registerRead(4)
        tscf.registerWritten(4)
        expected_events += ['thR', 'thW']
        check(tscf, delayed_calls=4, events=expected_events)
        self.clock.advance(.9)
        check(tscf, delayed_calls=4, events=expected_events)
        self.clock.advance(.1)
        expected_events += ['unthR', 'unthW']
        check(tscf, delayed_calls=2, events=expected_events)
        tscf.registerRead(1)
        tscf.registerWritten(1)
        check(tscf, delayed_calls=2, events=expected_events)

    def test_read_2_write_None(self):
        """Test readLimit > 0 and writeLimit = None"""
        tscf = self.create_factory(True, 2, None)
        # check that resetReadThisSecondID is running
        self.assertEqual(2, len(self.clock.getDelayedCalls()))
        tscf.registerRead(4)
        self.clock.advance(0.9)
        expected_events = ['thR']
        self.assertEqual(self.client.events, expected_events)
        self.clock.advance(0.9)
        expected_events += ['unthR']
        self.assertEqual(self.client.events, expected_events)
        self.clock.advance(.1)
        self.assertEqual(self.client.events, expected_events)
        # single throttling
        tscf.registerRead(2)
        self.clock.advance(0.1)
        expected_events += ['thR', 'unthR']
        self.assertEqual(self.client.events, expected_events)

    def test_read_None_write_2(self):
        """Test readLimit = None and writeLimit > 0"""
        tscf = self.create_factory(True, None, 2)
        # check that resetReadThisSecondID is running
        self.assertEqual(2, len(self.clock.getDelayedCalls()))
        tscf.registerWritten(4)
        self.clock.advance(0.9)
        expected_events = ['thW']
        self.assertEqual(self.client.events, expected_events)
        self.clock.advance(0.9)
        expected_events += ['unthW']
        self.assertEqual(self.client.events, expected_events)
        self.clock.advance(.1)
        self.assertEqual(self.client.events, expected_events)
        # single throttling (trigger a callLater(0, ..)
        tscf.registerWritten(2)
        self.clock.advance(0.1)
        expected_events += ['thW', 'unthW']
        self.assertEqual(self.client.events, expected_events)

    def test_change_read_to_None(self):
        """Test changing the read limit from > 0 to None."""
        tscf = self.create_factory(True, 2, None)
        self.assertEqual(2, len(self.clock.getDelayedCalls()))
        tscf.registerRead(4)
        expected_events = ['thR']
        self.assertEqual(self.client.events, expected_events)
        self.clock.advance(1.1)
        expected_events += ['unthR']
        self.assertEqual(self.client.events, expected_events)
        tscf.readLimit = None
        self.clock.advance(1)
        self.assertEqual(self.client.events, expected_events)
        tscf.registerRead(4)
        self.clock.advance(1.1)
        # no new events, throttling reads is off
        self.assertEqual(self.client.events, expected_events)

    def test_change_write_to_None(self):
        """Test changing the write limit from > 0 to None."""
        tscf = self.create_factory(True, None, 2)
        self.assertEqual(2, len(self.clock.getDelayedCalls()))
        tscf.registerWritten(4)
        expected_events = ['thW']
        self.assertEqual(self.client.events, expected_events)
        self.clock.advance(1.1)
        expected_events += ['unthW']
        self.assertEqual(self.client.events, expected_events)
        tscf.writeLimit = None
        self.clock.advance(1)
        self.assertEqual(self.client.events, expected_events)
        tscf.registerWritten(4)
        self.clock.advance(1.1)
        # no new events, throttling reads is off
        self.assertEqual(self.client.events, expected_events)


class TestEnablement(BaseThrottlingTestCase):
    """Tests for en/disabling throttling."""

    def test_disabling(self):
        """Tests that disabling throttling at runtime works as expected."""
        tscf = self.create_factory(True, 2, 2)
        self.assertNotEqual(None, tscf.resetReadThisSecondID)
        self.assertNotEqual(None, tscf.resetWriteThisSecondID)
        tscf.registerRead(2)
        tscf.registerWritten(2)
        self.assertNotEqual(None, tscf.unthrottleReadsID)
        self.assertNotEqual(None, tscf.unthrottleReadsID)
        self.clock.advance(1.1)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.assertEqual(None, tscf.unthrottleWritesID)
        tscf.disable_throttling()
        self.assertFalse(tscf.throttling_enabled,
                         "Throttling should be disabled.")
        for delayed in [tscf.unthrottleReadsID, tscf.resetReadThisSecondID,
                        tscf.unthrottleWritesID, tscf.resetWriteThisSecondID]:
            cancelled = delayed is None or delayed.cancelled
            self.assertTrue(cancelled)

    def test_enabling(self):
        """Tests that enabling throttling at runtime works as expected."""
        tscf = self.create_factory(False, 2, 2)
        self.assertEqual(None, tscf.resetReadThisSecondID)
        self.assertEqual(None, tscf.resetWriteThisSecondID)
        tscf.registerRead(2)
        tscf.registerWritten(2)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.clock.advance(1)
        self.assertEqual(None, tscf.unthrottleReadsID)
        self.assertEqual(None, tscf.unthrottleWritesID)
        self.assertEqual(None, tscf.resetReadThisSecondID)
        self.assertEqual(None, tscf.resetWriteThisSecondID)
        tscf.enable_throttling()
        self.assertTrue(
            tscf.throttling_enabled, "Throttling should be enabled.")
        self.assertNotEqual(None, tscf.resetReadThisSecondID)
        self.assertNotEqual(None, tscf.resetWriteThisSecondID)
        tscf.registerRead(3)
        tscf.registerWritten(3)
        for delayed in [tscf.unthrottleReadsID, tscf.resetReadThisSecondID,
                        tscf.unthrottleWritesID, tscf.resetWriteThisSecondID]:
            cancelled = delayed.cancelled
            self.assertFalse(cancelled)
