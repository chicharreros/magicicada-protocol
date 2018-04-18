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

"""A simple client with some tests."""

import os
import time
import math
import random
import zlib

from twisted.internet import reactor, defer

from magicicadaprotocol import request, protocol_pb2
from magicicadaprotocol.client import (
    StorageClientFactory, StorageClient)
from magicicadaprotocol.dircontent_pb2 import (
    DirectoryContent, DIRECTORY)


class NotDirectory(Exception):
    """This wasnt a directory"""


def delay_time(step):
    """generates a delay for each step"""
    return ((math.exp(step) - 1) / 10) / (1 + random.random())


def retry(function):
    """This function will be retried when it raises TRY_AGAIN from the server.
    """
    def inner(self, *args, **kwargs):
        """decorated."""

        def do_retry(failure, step):
            """retry."""
            if failure.check(request.StorageRequestError) \
                    and failure.value.error_message.error.type == \
                    protocol_pb2.Error.TRY_AGAIN:
                print "retry", args
                d = defer.Deferred()
                reactor.callLater(delay_time(step), d.callback, None)
                d.addCallback(lambda _: function(self, *args, **kwargs))
                d.addErrback(do_retry, step + 1)
                return d
            else:
                return failure
        d = function(self, *args, **kwargs)
        d.addErrback(do_retry, 0)
        return d
    return inner


class EasyClient(StorageClient):
    """Simple client that calls a callback on connection."""

    def __init__(self):
        """create a client."""
        StorageClient.__init__(self)
        self.cwd = "/"
        self.cwd_id = None

    def connectionMade(self):
        """Setup and call callback."""
        StorageClient.connectionMade(self)
        self.factory.clientConnectionMade(self)

    def _get_hash(self, node_id):
        """Get the hash of node_id."""
        def _got_query(query):
            """deferred part."""
            message = query[0][1].response[0]
            return message.hash

        d = self.query([(request.ROOT, node_id, request.UNKNOWN_HASH)])
        d.addCallback(_got_query)
        return d

    def _get_content(self, node):
        """get content"""
        d = self._get_hash(node)
        d.addCallback(lambda hash: self.get_content(request.ROOT, node, hash))
        d.addCallback(lambda result: zlib.decompress(result.data))
        return d

    def get_cwd_id(self):
        """get current working directory."""
        d = defer.Deferred()
        if self.cwd_id is None:
            d.addCallback(lambda _: self.get_root())
            d.addCallback(lambda result: setattr(self, "cwd_id", result))
            d.callback(None)
        else:
            d.callback(self.cwd_id)
        return d

    def chdir(self, path):
        """change cwd to path."""
        full_path = os.path.join(self.cwd, path)
        parts = [part for part in full_path.split("/") if part]

        def is_dir_return_id(parent, name):
            """check that this part of the path is a directory and return its
            id.
            """
            d = self._get_content(parent)

            def is_directory(content):
                """parse dircontent to find a directory with name == name."""
                unserialized_content = DirectoryContent()
                unserialized_content.ParseFromString(content)
                for entry in unserialized_content.entries:
                    if entry.name == name and entry.node_type == DIRECTORY:
                        print "is directory", entry
                        return entry.node
                raise NotDirectory("name %s is not a directory" % name)
            d.addCallback(is_directory)
            return d

        d = self.get_root()
        for part in parts:
            d.addCallback(is_dir_return_id, part)
        d.addCallback(lambda x: setattr(self, "cwd_id", x))
        d.addCallback(lambda x: setattr(self, "cwd", full_path))
        return d

    @retry
    def mkfile(self, name):
        """make a file named name in cwd."""
        d = self.get_cwd_id()
        d.addCallback(
            lambda _: self.make_file(request.ROOT, self.cwd_id, name))
        return d

    def mkdir(self, name):
        """make a dir named name in cwd."""
        d = self.get_cwd_id()
        d.addCallback(
            lambda _: self.make_dir(request.ROOT, self.cwd_id, name))
        return d

    def put(self, name, content):
        """put content into file named name."""
        pass

    def get(self, name):
        """get content from file names name."""
        d = self.get_id(name)
        d.addCallback(self._get_content)
        return d

    def unlink(self, name):
        """unlink file named name."""
        d = self.get_id(name)
        d.addCallback(self.unlink)
        return d

    def listdir(self):
        """get a dircontent list for cwd."""
        d = self.get_cwd()
        d.addCallback(self._get_content)

        def make_listdir(content):
            """parse dircontents."""
            result = []
            unserialized_content = DirectoryContent()
            unserialized_content.ParseFromString(content)
            for entry in unserialized_content.entries:
                result.append(entry)
            return result
        d.addCallback(make_listdir)
        return d

    def move(self, name, path, new_name=None):
        """move file."""
        if new_name is None:
            new_name = name


class EasyClientFactory(StorageClientFactory):
    """A test oriented protocol factory."""
    protocol = EasyClient

    def __init__(self, deferrer):
        """create a factory."""
        self.client = None
        self.defer = deferrer

    def clientConnectionMade(self, client_obj):
        """on client connection made."""
        self.client = client_obj
        self.defer.callback(self.client)

    def clientConnectionFailed(self, connector, reason):
        """We failed at connecting."""
        self.defer.errback(reason)


def client(host, port):
    """return a deferred that will succeed with a connected client."""
    d = defer.Deferred()
    factory = EasyClientFactory(d)
    reactor.connectTCP(host, port, factory)
    return d


def authenticated_client(host, port, token="open sesame"):
    """return a deferred that will succeed with an authenticated client."""
    d = client(host, port)

    def auth(client_obj):
        """do the auth."""
        d = client.dummy_authenticate(token)
        d.addCallback(lambda _: client_obj)
        return d
    d.addCallback(auth)
    return d


def skip_error(failure, error):
    """try: except $error: pass errback"""
    if failure.check(request.StorageRequestError) and \
            failure.value.error_message.error.type == error:
        return
    else:
        return failure


def skip_result(_, f, *args, **kwargs):
    """Deferred utilities."""
    return f(*args, **kwargs)


def sr_result(result, f, *args, **kwargs):
    """skip the result when calling the function and then return it."""
    f(*args, **kwargs)
    return result


def log(*args, **kwargs):
    """print args and kwargs."""
    for arg in args:
        print arg,
    print kwargs


def show_error(failure):
    """print the traceback."""
    print failure.getTraceback()


if __name__ == "__main__":

    def create_dirs(client_obj, num_dirs):
        """Create directories."""
        d = defer.succeed(None)
        for i in range(0, num_dirs):
            d.addCallback(skip_result, client_obj.mkdir, "%s" % (i))
            d.addErrback(skip_error, protocol_pb2.Error.ALREADY_EXISTS)
            d.addCallback(skip_result, log, "Directory %s created." % i)
        return d

    def make_files_client(client_obj, number, num_files):
        """Make files."""
        d = client_obj.chdir("%s" % (number))
        for i in range(0, num_files):
            d.addCallback(skip_result, log, "Client %s creating file %s."
                          % (number, i))
            d.addCallback(skip_result, client.mkfile, "%s" % (i))
            d.addCallback(skip_result, log, "Client %s created file %s."
                          % (number, i))
        return d

    NUM_CLIENTS = 200
    NUM_FILES = 50

    port_num = int(open("tmp/magicicada-api.port").read())
    deferred = authenticated_client("localhost", int(port_num))
    deferred.addCallback(create_dirs, NUM_CLIENTS)

    def fire_clients(_):
        """Fire off the client connections."""
        dlist = []
        for i in range(NUM_CLIENTS):
            d = authenticated_client("localhost", int(port_num))
            d.addCallback(sr_result, log, "client", i, "logged in")
            d.addCallback(make_files_client, i, NUM_FILES)
            d.addErrback(show_error)
            dlist.append(d)

        return defer.DeferredList(dlist)

    deferred.addCallback(fire_clients)
    deferred.addCallback(lambda _: reactor.stop())
    deferred.addErrback(show_error)
    print "Starting reactor"
    start_time = time.time()
    reactor.run()
