# Copyright 2015-2022  Chicharreros (https://launchpad.net/~chicharreros)
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

"""Test for proxy tunnel."""

import base64

from twisted.internet import defer
from twisted.internet.protocol import Protocol, ClientFactory, connectionDone
from twisted.internet.testing import StringTransport
from twisted.trial.unittest import TestCase as TwistedTestCase

from magicicadaprotocol.proxy_tunnel import ProxyTunnelFactory


class FakeTransport(StringTransport):
    """Fake transport"""

    def __init__(self, reply_func, remote_func=None):
        """Initialization for fake transport"""
        super().__init__()
        self.reply_func = reply_func
        self.remote_func = remote_func
        self.done = False

    def write(self, data):
        """Write some data"""
        super().write(data)
        if not self.done:
            if b"\r\n\r\n" in self.value():
                self.done = True
                self.reply_func(self.value())

        else:
            if self.remote_func is not None:
                self.remote_func(self.value())

    def writeSequence(self, data):
        """Write a sequence"""
        self.write(b''.join(data))

    def startTLS(self, *args, **kwargs):
        """Fake starttls"""
        self.clear()


class FakeConnectHTTPS(object):
    """Fake HTTPS Connection"""
    def __init__(self, host, port, factory, proxy_callback,
                 user=None, passwd=None, peer_callback=None):
        """FakeConnectHTTPS initialization"""
        self.transport = FakeTransport(
            self.proxy_callback, self.peer_callback)

        self.proxy_callback_f = proxy_callback
        self.peer_callback_f = peer_callback
        pt_factory = ProxyTunnelFactory(host, port, factory, user, passwd)

        self.factory = factory
        self.protocol = pt_factory.buildProtocol(self.transport.getPeer())
        self.protocol.makeConnection(self.transport)

    def proxy_callback(self, data):
        """Proxy callback"""
        self.proxy_callback_f(data, self.protocol, self.factory)

    def peer_callback(self, data):
        """Peer callback"""
        self.peer_callback_f(data, self.protocol, self.factory)


def make_server(proxy_callback, peer_callback, auth):
    """Make a server"""
    d = defer.Deferred()

    class TestClient(Protocol):
        """Test the Client"""

        def __init__(self):
            """Initialize ourselves"""
            pass

        def connectionMade(self):
            """Connection succeeded"""
            d.callback("done")

    class TestClientFactory(ClientFactory):
        """Factory for test client"""
        protocol = TestClient

        def __init__(self):
            """Initialize ourselves"""
            pass

        def clientConnectionFailed(self, connector, reason):
            """Connection failed"""
            d.errback(Exception("failed"))
    if auth:
        user, passwd = auth.split(":")
    else:
        user, passwd = None, None
    FakeConnectHTTPS("test", 1, TestClientFactory(), proxy_callback,
                     user, passwd, peer_callback)
    return d


def test_response(response_string, auth=None):
    """Test the response"""

    assert isinstance(response_string, bytes), (
        '%r should be bytes' % response_string)

    def response(data, proto, fact):
        """Response callback"""
        if auth is not None:
            auth_line = (
                b"Proxy-Authorization: Basic " +
                base64.b64encode(b"test:test"))
            if auth_line not in data:
                proto.dataReceived(b"HTTP/1.0 403 Forbidden\r\n\r\n")
            else:
                proto.dataReceived(response_string)
        else:
            proto.dataReceived(response_string)

    return make_server(response, lambda x, y, z: None, auth)


class TunnelTests(TwistedTestCase):
    """Test the proxy tunnel"""
    def test_connect(self):
        """Test connecting"""
        return test_response(b"HTTP/1.0 200 Connection Made\r\n\r\n")

    def test_connect_failure(self):
        """Test connection failure"""
        d = defer.Deferred()
        d2 = test_response(b"HTTP/1.0 503 Service Unavailable\r\n\r\n")
        d2.addCallbacks(
            lambda r: d.errback(Exception("error: connection made")),
            lambda r: d.callback("ok"))
        return d

    def test_auth_required(self):
        """Test auth requriement"""
        d = defer.Deferred()
        d2 = test_response(
            b"HTTP/1.0 407 Proxy Authentication Required\r\n\r\n")
        d2.addCallbacks(
            lambda r: d.errback(Exception("error: connection made")),
            lambda r: d.callback("ok"))
        return d

    def test_connect_auth(self):
        """Test connecting with auth"""
        return test_response(
            b"HTTP/1.0 200 Connection Made\r\n\r\n", auth="test:test")

    def test_auth_error(self):
        """Test auth failure"""
        d = defer.Deferred()
        d2 = test_response(b"HTTP/1.0 200 Connection Made\r\n\r\n",
                           auth="test:notthepassword")
        d2.addCallbacks(
            lambda r: d.errback(Exception("error: connection made")),
            lambda r: d.callback("ok"))
        return d

    def test_echo(self):
        """Test echo"""
        d = defer.Deferred()

        def response(data, proto, fact):
            """Response callback"""
            proto.dataReceived(b"HTTP/1.0 200 Connection Made\r\n\r\n")

        def peer_callback(data, proto, fact):
            """Peer callback"""
            proto.dataReceived(data)

        class TestClient(Protocol):
            """Test echo Client"""
            __message = b"hello world!"

            def __init__(self):
                """Initialize ourselves"""
                pass

            def connectionMade(self):
                """Connection succeeded"""
                self.transport.write(self.__message)

            def dataReceived(self, data):
                """Data received"""
                if data == self.__message:
                    d.callback("ok")
                else:
                    d.errback(Exception("wrong data: %s" % data))

        class TestClientFactory(ClientFactory):
            """Factory for test echo client"""
            protocol = TestClient

            def __init__(self):
                """Initialize ourselves"""
                pass

            def clientConnectionFailed(self, connector, reason):
                """Connection failed"""
                d.errback(Exception("failed"))
        FakeConnectHTTPS("test", 1, TestClientFactory(),
                         response, peer_callback=peer_callback)
        return d

    def test_connection_lost(self):
        """Test connection loss"""
        d = defer.Deferred()

        def response(data, proto, fact):
            """Response callback"""
            proto.dataReceived(b"HTTP/1.0 200 Connection Made\r\n\r\n")

        def peer_callback(data, proto, fact):
            """Peer callback"""
            proto.connectionLost(b"goodbye")

        class TestClient(Protocol):
            """Test client"""

            def __init__(self):
                """Initialize ourselves"""
                pass

            def connectionMade(self):
                """Connection succeeded"""
                self.transport.write(b"die")

            def connectionLost(self, reason=connectionDone):
                """Connection lost"""
                d.callback(b"ok")

        class TestClientFactory(ClientFactory):
            """Factory for test client"""
            protocol = TestClient

            def __init__(self):
                """Initialize ourselves"""
                pass

            def clientConnectionFailed(self, connector, reason):
                """Connection failed"""
                d.errback(Exception("failed"))

        FakeConnectHTTPS("test", 1, TestClientFactory(),
                         response, peer_callback=peer_callback)
        return d
