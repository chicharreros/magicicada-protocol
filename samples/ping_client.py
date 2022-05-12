# -*- coding: utf-8 -*-
#
# Copyright 2009-2012 Canonical Ltd.
# Copyright 2015-2018 Chicharreros (https://launchpad.net/~chicharreros)
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

"""A simple ping client."""

from twisted.internet import reactor

from magicicadaprotocol.client import StorageClientFactory, StorageClient


class PingClient(StorageClient):
    """Simple client that calls a callback on connection."""

    def connectionMade(self):
        """Setup and call callback."""
        StorageClient.connectionMade(self)
        print("Connection made.")
        d = self.ping()

        def done(request):
            """We have the ping reply"""
            print("Ping RTT:", request.rtt)
            reactor.stop()

        def error(failure):
            """Something went wrong."""
            print("Error:")
            print(failure.getTraceback())
            reactor.stop()

        d.addCallbacks(done, error)


class PingClientFactory(StorageClientFactory):
    """A test oriented protocol factory."""

    protocol = PingClient

    def clientConnectionFailed(self, connector, reason):
        """We failed at connecting."""

        print('Connection failed. Reason:', reason)
        reactor.stop()


if __name__ == "__main__":
    # these 3 lines show the different ways of connecting a client to the
    # server

    # using tcp
    reactor.connectTCP('75.101.137.174', 80, PingClientFactory())

    # using ssl
    # reactor.connectSSL('localhost', 20101, StorageClientFactory(),
    #           ssl.ClientContextFactory())

    # using ssl over a proxy
    # from magicicadaprotocol import proxy_tunnel
    # proxy_tunnel.connectHTTPS('localhost', 3128,
    #        'localhost', 20101, StorageClientFactory(),
    #        user="test", passwd="test")

    reactor.run()
