# -*- coding: utf-8 -*-
#
# Copyright 2009 Canonical Ltd.
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
"""setup.py"""

import glob
import os
import sys
import subprocess

from distutils.spawn import find_executable
from distutils.command import clean, build
from setuptools import find_packages, setup


class StorageProtocolBuild(build.build):
    """Class to build the protobuf files."""

    description = "build the protocol buffers with protobuf-compiler"

    def run(self):
        """Do the build"""
        protoc = find_executable("protoc")
        if protoc is None:
            sys.stderr.write(
                "*** Cannot find protoc; is the protobuf-compiler"
                " package installed?\n"
            )
            sys.exit(-1)

        for source in glob.glob('magicicadaprotocol/*.proto'):
            # glob works with unix and does not like \ in the search path,
            # we use / and correct the issue on windows when appropiate
            if sys.platform == "win32":
                source = source.replace('/', '\\')
            args = (protoc, '--python_out=.', source)
            if subprocess.call(args) != 0:
                sys.exit(-1)

        build.build.run(self)


class StorageProtocolClean(clean.clean):
    """Class to clean up the built protobuf files."""

    description = "clean up files generated by protobuf-compiler"

    def run(self):
        """Do the clean up"""
        for source in glob.glob("magicicadaprotocol/*_pb2.py"):
            os.unlink(source)

        # Call the parent class clean command
        clean.clean.run(self)


setup(
    name='magicicadaprotocol',
    version='3.0.3',
    description=(
        'The protocol implementation for the Magicicada filesync server '
        '(open source fork of the Ubuntu One filesync).'
    ),
    # From twisted - UserWarning: You do not have a working installation of the
    # service_identity module: 'No module named service_identity'.  Please
    # install it from <https://pypi.python.org/pypi/service_identity> and make
    # sure all of its dependencies are satisfied.  Without the service_identity
    # module, Twisted can perform only rudimentary TLS client hostname
    # verification. Many valid certificate/hostname mappings may be rejected.
    install_requires=[
        'pyOpenSSL',
        'protobuf',
        'service_identity',
        'twisted',
        'zope.interface',
    ],
    packages=find_packages(),
    cmdclass={'build': StorageProtocolBuild, 'clean': StorageProtocolClean},
)
