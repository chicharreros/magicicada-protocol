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

"""Some storage protocol utils."""

import logging
import time

from functools import partial

from twisted.internet import defer
from twisted.python import log
from twisted.web import http

log_debug = partial(log.msg, loglevel=logging.DEBUG)


class BaseTimestampChecker:
    """A timestamp that's regularly checked with a server."""

    CHECKING_INTERVAL = 60 * 60  # in seconds
    ERROR_INTERVAL = 30  # in seconds
    SERVER_URL = "http://one.ubuntu.com/api/time"

    def __init__(self):
        """Initialize this instance."""
        self.next_check = time.time()
        self.skew = 0

    def get_server_date_header(self, server_url):
        """Return a deferred with the server time, using your web client."""
        return defer.fail(NotImplementedError())

    @defer.inlineCallbacks
    def get_server_time(self):
        """Get the time at the server."""
        date_string = yield self.get_server_date_header(self.SERVER_URL)
        timestamp = http.stringToDatetime(date_string)
        defer.returnValue(timestamp)

    @defer.inlineCallbacks
    def get_faithful_time(self):
        """Get an accurate timestamp."""
        local_time = time.time()
        if local_time >= self.next_check:
            try:
                server_time = yield self.get_server_time()
                self.next_check = local_time + self.CHECKING_INTERVAL
                self.skew = server_time - local_time
                log_debug("Calculated server-local time skew:", self.skew)
            except Exception as e:
                log_debug("Error while verifying the server time skew:", e)
                self.next_check = local_time + self.ERROR_INTERVAL
        log_debug("Using corrected timestamp:",
                  http.datetimeToString(local_time + self.skew))
        defer.returnValue(int(local_time + self.skew))
