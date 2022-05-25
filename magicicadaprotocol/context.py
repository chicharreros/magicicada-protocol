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

"""Standard Routines for working with ssl context creation."""

import os

from OpenSSL import SSL
from twisted.internet import error, ssl
from twisted.python import log


class HostnameVerifyContextFactory(ssl.CertificateOptions):
    """Does hostname checks in addition to certificate checks."""

    def __init__(self, hostname, *args, **kwargs):
        """Initialize this instance."""
        super(HostnameVerifyContextFactory, self).__init__(*args, **kwargs)
        self.expected_hostname = hostname

    def verify_server_hostname(self, conn, cert, errno, depth, preverifyOK):
        """Verify the server hostname."""
        if depth == 0:
            # No extra checks because U1 certs have the right commonName
            if self.expected_hostname != cert.get_subject().commonName:
                log.err("Host name does not match certificate. "
                        "Expected %s but got %s." % (
                            self.expected_hostname,
                            cert.get_subject().commonName))
                return False
        return preverifyOK

    def getContext(self):
        """The context returned will verify the hostname too."""
        ctx = super(HostnameVerifyContextFactory, self).getContext()
        flags = SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT
        ctx.set_verify(flags, self.verify_server_hostname)
        return ctx


def get_certificates():
    """Get a list of certificate paths."""
    ssl_cert_location = os.environ['SSL_CERTIFICATES_DIR']
    ca_files = []
    digests = set()
    for fname in os.listdir(ssl_cert_location):
        full_path = os.path.join(ssl_cert_location, fname)
        if os.path.isdir(full_path) or not fname.endswith(".pem"):
            continue
        with open(full_path, 'r') as fd:
            data = fd.read()
        if 'BEGIN CERTIFICATE' in data:
            ca_file = ssl.Certificate.loadPEM(data)
            # avoid adding the same cert twice as openssl doesn't like it
            digest = ca_file.original.digest("sha1")
            if digest in digests:
                continue
            digests.add(digest)
            ca_files.append(ca_file.original)
        else:
            log.err("Cannot load certificate at %s, ignoring.", full_path)

    return ca_files


def get_ssl_context(no_verify, hostname=None):
    """Get the ssl context."""
    if no_verify:
        ctx = ssl.ClientContextFactory()
    else:
        if hostname is None:
            raise error.CertificateError(
                'No hostname specified. Unable to verify SSL certificate.')
        ctx = HostnameVerifyContextFactory(hostname, verify=True,
                                           caCerts=get_certificates(),
                                           method=SSL.SSLv23_METHOD)
    return ctx
