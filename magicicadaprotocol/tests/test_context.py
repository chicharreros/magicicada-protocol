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

import os

from OpenSSL import crypto, SSL
from twisted.internet import defer, error, reactor, ssl
from twisted.trial import unittest
from twisted.web import client, resource, server

from magicicadaprotocol import context


class FakeCerts(object):
    """CA and Server certificate."""

    def __init__(self, testcase, common_name="fake.domain"):
        """Initialize this fake instance."""
        self.cert_dir = os.path.join(testcase.mktemp(), 'certs')
        if not os.path.exists(self.cert_dir):
            os.makedirs(self.cert_dir)

        ca_key = self._build_key()
        ca_req = self._build_request(ca_key, "Fake Cert Authority")
        self.ca_cert = self._build_cert(ca_req, ca_req, ca_key)

        server_key = self._build_key()
        server_req = self._build_request(server_key, common_name)
        server_cert = self._build_cert(server_req, self.ca_cert, ca_key)

        self.server_key_path = self._save_key(server_key, "server_key.pem")
        self.server_cert_path = self._save_cert(server_cert, "server_cert.pem")

    def _save_key(self, key, filename):
        """Save a certificate."""
        data = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
        return self._save(filename, data)

    def _save_cert(self, cert, filename):
        """Save a certificate."""
        data = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        return self._save(filename, data)

    def _save(self, filename, data):
        """Save a key or certificate, and return the full path."""
        fullpath = os.path.join(self.cert_dir, filename)
        if os.path.exists(fullpath):
            os.unlink(fullpath)
        with open(fullpath, 'wb') as fd:
            fd.write(data)
        return fullpath

    def _build_key(self):
        """Create a private/public key, save it in a temp dir."""
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 1024)
        return key

    def _build_request(self, key, common_name):
        """Create a new certificate request."""
        request = crypto.X509Req()
        request.get_subject().CN = common_name
        request.set_pubkey(key)
        request.sign(key, "sha256")
        return request

    def _build_cert(self, request, ca_cert, ca_key):
        """Create a new certificate."""
        certificate = crypto.X509()
        certificate.set_serial_number(1)
        certificate.set_issuer(ca_cert.get_subject())
        certificate.set_subject(request.get_subject())
        certificate.set_pubkey(request.get_pubkey())
        certificate.gmtime_adj_notBefore(0)
        certificate.gmtime_adj_notAfter(3600)  # valid for one hour
        certificate.sign(ca_key, "sha256")
        return certificate


class FakeResource(resource.Resource):
    """A fake resource."""

    isLeaf = True

    def render(self, request):
        """Render this resource."""
        return b"ok"


class SSLContextTestCase(unittest.TestCase):
    """Tests for the context.get_ssl_context function."""

    @defer.inlineCallbacks
    def verify_context(self, server_context, client_context):
        """Verify a client context with a given server context."""
        site = server.Site(FakeResource())
        port = reactor.listenSSL(0, site, server_context)
        self.addCleanup(port.stopListening)
        url = b"https://localhost:%d" % port.getHost().port
        result = yield client.getPage(url, contextFactory=client_context)
        self.assertEqual(result, b"ok")

    @defer.inlineCallbacks
    def assert_cert_failed_verify(self, server_context, client_context):
        d = self.verify_context(server_context, client_context)
        e = yield self.assertFailure(d, SSL.Error)
        self.assertEqual(len(e.args), 1)
        expected = [('SSL routines', '', 'certificate verify failed')]
        self.assertEqual(e.args[0], expected)

    @defer.inlineCallbacks
    def test_no_verify(self):
        """Test the no_verify option."""
        certs = FakeCerts(self, "localhost")
        server_context = ssl.DefaultOpenSSLContextFactory(
            certs.server_key_path, certs.server_cert_path)
        client_context = context.get_ssl_context(no_verify=True,
                                                 hostname="localhost")

        yield self.verify_context(server_context, client_context)

    def test_no_hostname(self):
        """Test that calling without hostname arg raises proper error."""
        self.assertRaises(error.CertificateError,
                          context.get_ssl_context, False)

    @defer.inlineCallbacks
    def test_fails_certificate(self):
        """A wrong certificate is rejected."""
        certs = FakeCerts(self, "localhost")
        server_context = ssl.DefaultOpenSSLContextFactory(
            certs.server_key_path, certs.server_cert_path)
        client_context = context.get_ssl_context(no_verify=False,
                                                 hostname="localhost")

        yield self.assert_cert_failed_verify(server_context, client_context)

    @defer.inlineCallbacks
    def test_fails_hostname(self):
        """A wrong hostname is rejected."""
        certs = FakeCerts(self, "thisiswronghost.net")
        server_context = ssl.DefaultOpenSSLContextFactory(
            certs.server_key_path, certs.server_cert_path)
        self.patch(context, "get_certificates", lambda: [certs.ca_cert])
        client_context = context.get_ssl_context(no_verify=False,
                                                 hostname="localhost")
        yield self.assert_cert_failed_verify(server_context, client_context)

    @defer.inlineCallbacks
    def test_matches_all(self):
        """A valid certificate passes checks."""
        certs = FakeCerts(self, "localhost")
        server_context = ssl.DefaultOpenSSLContextFactory(
            certs.server_key_path, certs.server_cert_path)
        self.patch(context, "get_certificates", lambda: [certs.ca_cert])
        client_context = context.get_ssl_context(no_verify=False,
                                                 hostname="localhost")

        yield self.verify_context(server_context, client_context)


class CertLoadingTestCase(unittest.TestCase):
    """Tests for the get_certificates function."""

    def test_load_all_certificates(self):
        """Load all available certificates."""
        certs = FakeCerts(self, "localhost")
        os.environ['SSL_CERTIFICATES_DIR'] = certs.cert_dir
        # remove the key
        os.unlink(certs.server_key_path)
        loaded = context.get_certificates()
        expected = []
        for cert_file in os.listdir(certs.cert_dir):
            if not cert_file.endswith('.pem'):
                continue
            with open(os.path.join(certs.cert_dir, cert_file), 'r') as fd:
                ca_file = ssl.Certificate.loadPEM(fd.read())
                expected.append(ca_file.original.digest("sha1"))

        certs = set(cert.digest("sha1") for cert in loaded)
        self.assertFalse(certs.difference(set(expected)))

    @defer.inlineCallbacks
    def test_use_all_certificates_and_fail(self):
        """Use system installed certificates and fail checking self-signed."""
        certs = FakeCerts(self, "localhost")
        os.environ['SSL_CERTIFICATES_DIR'] = certs.cert_dir
        server_context = ssl.DefaultOpenSSLContextFactory(
            certs.server_key_path, certs.server_cert_path)
        client_context = context.get_ssl_context(no_verify=False,
                                                 hostname="localhost")
        site = server.Site(FakeResource())
        port = reactor.listenSSL(0, site, server_context)
        self.addCleanup(port.stopListening)
        url = b"https://localhost:%d" % port.getHost().port
        yield self.assertFailure(
            client.getPage(url, contextFactory=client_context), SSL.Error)
