Magicicada Protocol
===================

![tests](https://github.com/chicharreros/magicicada-protocol/actions/workflows/tests.yml/badge.svg)

This package contains definitions for the protocol messages used by the
Magicicada file storage/sharing service (open source fork of Ubuntu One).


Details
-------

The protocol message definitions here are provided as Google Protocol
Buffer (.proto) files (see
http://code.google.com/apis/protocolbuffers/docs/overview.html).
These are compiled to Python using Google's "protoc" tool, which is
available on Ubuntu via the protobuf-compiler package, and use the
python-protobuf bindings.  The package may be built and installed in the
usual fashion using the python setup tools (python setup.py build &&
sudo python setup.py install).

However, note that unless you are very comfortable with what you are
doing, if you are installing on an Ubuntu system it is probably better
to build and install a Debian package.  Recent versions of Ubuntu do not
load python modules from /usr/local by default, and you are likely to
already have an installed magicicadaprotocol package in any case.

Protocol Overview:

Since it is not well-documented elsewhere, I'll also give a very brief
outline of the protocol interactions here.

Most client/server communication is in the form of client-initiated
requests.  Each message from the client initiating a request is given
a request ID which is intended to be unique for the lifetime of the
connection.

The actual method for generating request IDs doesn't matter as long as
they are even numbers (e.g. 0, 2, 4, ...) and aren't re-used by different
requests on the same connection (but note that some requests may involve
multiple messages).  Server responses to a client request will use the
client-supplied request ID, but server-originated messages will have a
server-assigned ID which is odd (e.g. 1, 3, 5, ...).  In effect, when the
low bit of the request ID is set, it indicates a server-initiated request.

The protocol is asynchronous in that multiple requests may be "in flight"
at once, their messages (if there are multiple messages in the
request) arbitrarily interleaved.

The main exception to the rule that communication is client-initiated are
node state change notifications.  A client will receive unsolicited node
state messages from the server whenever a node (a file or directory) in
the user's storage (or in any shares which the user has accepted) changes.

At present, node state extends to the hash (currently a sha1) of a
node's content, but may later extend to metadata like executable flags
and so on.  In addition to these "push" notifications, node state messages
may be sent in response to explicit requests by the client.

Every node in the storage system is identified by a UUID, and every node
(whether a file or a directory) has content associated with it.  For
directories, that content will be a sorted enumeration of the directory's
contents, serialized using the structures defined in dircontent.proto.

When downloading the content of a node, the client and server have a
brief exchange followed by a series of messages bearing data, all with
the same request id.  Uploads work similarly -- in both cases, the request
ID identifies a particular in-progress upload or download.
