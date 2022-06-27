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

"""Tests for the protocol client."""

import io
import sys
import uuid
from collections import defaultdict

from twisted.application import internet, service
from twisted.internet import defer
from twisted.internet.defer import Deferred
from twisted.trial.unittest import TestCase
from twisted.web import server, resource

from magicicadaprotocol import delta, protocol_pb2, request, sharersp, volumes
from magicicadaprotocol.client import (
    Authenticate,
    BytesMessageProducer,
    ChangePublicAccess,
    CreateUDF,
    DeleteVolume,
    GetDelta,
    ListPublicFiles,
    ListVolumes,
    MakeDir,
    MakeFile,
    Move,
    PutContent,
    StorageClient,
    Unlink,
)

from magicicadaprotocol.tests import test_delta_info


PATH = '~/Documents/pdfs/moño/'
NAME = 'UDF-me'
VOLUME = uuid.UUID('12345678-1234-1234-1234-123456789abc')
SHARE = uuid.UUID('33333333-1234-1234-1234-123456789abc')
NODE = uuid.UUID('FEDCBA98-7654-3211-2345-6789ABCDEF12')
USER = 'Dude'
GENERATION = 999
PUBLIC_URL = "http://magicicada/someid"


class FakedError(Exception):
    """Stub to replace Request.error."""


def stub_function(*args, **kwargs):
    """Stub to replace non-related functions."""
    return None


def faked_error(message):
    """Stub to replace Request.error."""
    raise FakedError


def was_called(self, flag):
    """Helper to assert a function was called."""
    assert not getattr(self, flag)

    def set_flag(*args, **kwargs):
        """Record the calling was made."""
        setattr(self, flag, True)
    return set_flag


def build_list_volumes():
    """Build a LIST_VOLUMES message."""
    message = protocol_pb2.Message()
    message.type = protocol_pb2.Message.VOLUMES_INFO
    return message


def build_volume_created():
    """Build VOLUME_CREATED message."""
    message = protocol_pb2.Message()
    message.type = protocol_pb2.Message.VOLUME_CREATED
    return message


def build_volume_deleted():
    """Build VOLUME_DELETED message."""
    message = protocol_pb2.Message()
    message.type = protocol_pb2.Message.VOLUME_DELETED
    return message


def set_root_message(message):
    """Set a simple Root message."""
    message.type = protocol_pb2.Volumes.ROOT
    message.root.node = str(NODE)


def set_udf_message(message):
    """Set a simple UDFs message."""
    message.type = protocol_pb2.Volumes.UDF
    message.udf.volume = str(VOLUME)
    message.udf.node = str(NODE)
    message.udf.suggested_path = PATH


def set_share_message(message):
    """Set a simple Share message."""
    message.type = protocol_pb2.Volumes.SHARE
    message.share.share_id = str(VOLUME)
    message.share.direction = 0
    message.share.subtree = str(NODE)
    message.share.share_name = 'test'
    message.share.other_username = USER
    message.share.other_visible_name = USER
    message.share.accepted = False
    message.share.access_level = 0


def noop_callback(*a):
    """No op callback."""


class DummyAttribute(object):
    """Helper class to replace non-related classes."""

    def __getattribute__(self, name):
        """Attributes can be whatever we need."""
        return stub_function


class FakedProtocol(StorageClient):
    """Fake StorageClient to avoid twisted."""

    def __init__(self, *args, **kwargs):
        """Override transports and keep track of messages."""
        StorageClient.__init__(self, *args, **kwargs)
        self.transport = DummyAttribute()
        self.recorder = defaultdict(list)

    @property
    def messages(self):
        return self.recorder['sent']

    def sendMessage(self, message):
        """Keep track of messages."""
        self.recorder['sent'].append(message)

    def processMessage(self, message):
        """Keep track of messages."""
        self.recorder['received'].append(message)


class ClientTestCase(TestCase):
    """Check that MultiQuery works using an iterator."""

    def setUp(self):
        """Initialize testing client."""
        self.client = FakedProtocol()
        self.called = False
        self.volume = None

    def test_init_maxpayloadsize(self):
        """Get the value from the constant at init time."""
        self.assertEqual(self.client.max_payload_size,
                         request.MAX_PAYLOAD_SIZE)

    def test_data_received_index_error(self):
        self.client.dataReceived(b'foo bar')
        self.assertEqual(self.client.recorder, {})

    def test_data_received_handles_bytes(self):
        protocol_version = b'\r\n\x00\x00\x00\x08\x08\x01\x10\x05"\x02\x08\x03'
        self.client.dataReceived(protocol_version)
        messages = self.client.recorder['received']
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], protocol_pb2.Message)

    # client to server
    def test_client_get_delta(self):
        """Get a delta."""
        self.patch(GetDelta, 'start', was_called(self, 'called'))

        result = self.client.get_delta(share_id=SHARE, from_generation=0)
        self.assertTrue(self.called, 'GetDelta.start() was called')
        self.assertIsInstance(result, Deferred)

    def test_client_get_delta_from_scratch(self):
        """Get a delta from scratch."""
        self.patch(GetDelta, 'start', was_called(self, 'called'))

        result = self.client.get_delta(share_id=SHARE, from_scratch=True)
        self.assertTrue(self.called, 'GetDelta.start() was called')
        self.assertIsInstance(result, Deferred)

    def test_client_get_delta_bad(self):
        """Require from_generation or from_scratch."""

        self.assertRaises(TypeError, self.client.get_delta,
                          share_id=SHARE, callback=1)

    def test_create_udf(self):
        """Test create_udf."""
        self.patch(CreateUDF, 'start', was_called(self, 'called'))

        result = self.client.create_udf(path=PATH, name=NAME)
        self.assertTrue(self.called, 'CreateUDF.start() was called')
        self.assertIsInstance(result, Deferred)

    def test_list_volumes(self):
        """Test list_volumes."""
        self.patch(ListVolumes, 'start', was_called(self, 'called'))

        result = self.client.list_volumes()
        self.assertTrue(self.called, 'ListVolumes.start() was called')
        self.assertIsInstance(result, Deferred)

    def test_delete_volume(self):
        """Test delete_volume."""
        self.patch(DeleteVolume, 'start', was_called(self, 'called'))

        result = self.client.delete_volume(volume_id=VOLUME)
        self.assertTrue(self.called, 'DeleteVolume.start() was called')
        self.assertIsInstance(result, Deferred)

    def test_set_volume_deleted_callback(self):
        """Test callback setting."""
        self.client.set_volume_deleted_callback(noop_callback)
        self.assertTrue(self.client._volume_deleted_callback is noop_callback)

    def test_callback_must_be_callable(self):
        """Test set callback parameters."""
        self.assertRaises(TypeError, self.client.set_volume_created_callback,
                          'hello')

        self.assertRaises(TypeError, self.client.set_volume_deleted_callback,
                          'world')

        self.assertRaises(TypeError,
                          self.client.set_volume_new_generation_callback, 'fu')

    def test_set_volume_created_callback(self):
        """Test callback setting."""
        self.client.set_volume_created_callback(noop_callback)
        self.assertIs(self.client._volume_created_callback, noop_callback)

    def test_set_volume_new_generation_callback(self):
        """Test callback setting."""
        self.client.set_volume_new_generation_callback(noop_callback)
        self.assertIs(self.client._volume_new_generation_callback,
                      noop_callback)

    # share notification callbacks
    def test_share_change_callback(self):
        """Test share_change callback usage."""
        self.assertRaises(TypeError, self.client.set_share_change_callback,
                          'hello')
        # create a response and message
        share_resp = sharersp.NotifyShareHolder.from_params(
            uuid.uuid4(), uuid.uuid4(), 'sname', 'byu', 'tou', 'View')
        proto_msg = protocol_pb2.Message()
        proto_msg.type = protocol_pb2.Message.NOTIFY_SHARE
        share_resp.dump_to_msg(proto_msg.notify_share)

        # wire up a call back and make sure it's correct
        self.share_notif = None

        def a_callback(notif):
            setattr(self, 'share_notif', notif)

        self.client.set_share_change_callback(a_callback)
        self.assertTrue(self.client._share_change_callback is a_callback)
        self.client.handle_NOTIFY_SHARE(proto_msg)
        self.assertEqual(self.share_notif.share_id, share_resp.share_id)

    def test_share_delete_callback(self):
        """Test share_delete callback usage."""
        self.assertRaises(TypeError, self.client.set_share_delete_callback,
                          'hello')

        share_id = uuid.uuid4()
        proto_msg = protocol_pb2.Message()
        proto_msg.type = protocol_pb2.Message.SHARE_DELETED
        proto_msg.share_deleted.share_id = str(share_id)

        # wire up a call back and make sure it's correct
        self.deleted_share_id = None

        def a_callback(notif):
            setattr(self, 'deleted_share_id', notif)

        self.client.set_share_delete_callback(a_callback)
        self.assertTrue(self.client._share_delete_callback is a_callback)
        self.client.handle_SHARE_DELETED(proto_msg)
        self.assertEqual(self.deleted_share_id, share_id)

    def test_share_answer_callback(self):
        """Test share_answer callback usage."""
        self.assertRaises(TypeError, self.client.set_share_answer_callback,
                          'hello')

        share_id = uuid.uuid4()
        proto_msg = protocol_pb2.Message()
        proto_msg.type = protocol_pb2.Message.SHARE_ACCEPTED
        proto_msg.share_accepted.share_id = str(share_id)
        proto_msg.share_accepted.answer = protocol_pb2.ShareAccepted.YES

        # wire up a call back and make sure it's correct
        self.answer = None

        def a_callback(s, a):
            setattr(self, 'answer', (s, a))

        self.client.set_share_answer_callback(a_callback)
        self.assertTrue(self.client._share_answer_callback is a_callback)
        self.client.handle_SHARE_ACCEPTED(proto_msg)
        self.assertEqual(self.answer[0], share_id)
        self.assertEqual(self.answer[1], "Yes")

    def test_handle_volume_new_generation_uuid(self):
        """Test handle_VOLUME_NEW_GENERATION with an uuid id."""
        # set the callback to record the info
        called = []
        self.client.set_volume_new_generation_callback(
            lambda *a: called.append(a))

        # create the message
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.VOLUME_NEW_GENERATION
        volume_id = uuid.uuid4()
        message.volume_new_generation.volume = str(volume_id)
        message.volume_new_generation.generation = 77

        # send the message, and assert the callback is called with good info
        self.client.handle_VOLUME_NEW_GENERATION(message)
        self.assertEqual(called[0], (volume_id, 77))

    def test_handle_volume_new_generation_root(self):
        """Test handle_VOLUME_NEW_GENERATION for ROOT."""
        # set the callback to record the info
        called = []
        self.client.set_volume_new_generation_callback(
            lambda *a: called.append(a))

        # create the message
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.VOLUME_NEW_GENERATION
        message.volume_new_generation.volume = request.ROOT
        message.volume_new_generation.generation = 77

        # send the message, and assert the callback is called with good info
        self.client.handle_VOLUME_NEW_GENERATION(message)
        self.assertEqual(called[0], (request.ROOT, 77))

    # server to client
    def test_handle_volume_created(self):
        """Test handle_VOLUME_CREATED."""
        a_callback = was_called(self, 'called')
        self.client.set_volume_created_callback(a_callback)

        message = build_volume_created()
        set_root_message(message.volume_created)
        self.client.handle_VOLUME_CREATED(message)

        self.assertTrue(self.called)

    def test_handle_root_created_passes_a_root(self):
        """Test handle_VOLUME_CREATED parameter passing."""
        self.volume = None

        def a_callback(vol):
            setattr(self, 'volume', vol)

        self.client.set_volume_created_callback(a_callback)

        message = build_volume_created()
        set_root_message(message.volume_created)
        root = volumes.RootVolume.from_msg(message.volume_created.root)

        self.client.handle_VOLUME_CREATED(message)
        self.assertEqual(root, self.volume)

    def test_handle_udf_created_passes_a_udf(self):
        """Test handle_VOLUME_CREATED parameter passing."""
        self.volume = None

        def a_callback(vol):
            setattr(self, 'volume', vol)

        self.client.set_volume_created_callback(a_callback)

        message = build_volume_created()
        set_udf_message(message.volume_created)
        udf = volumes.UDFVolume.from_msg(message.volume_created.udf)

        self.client.handle_VOLUME_CREATED(message)
        self.assertEqual(udf, self.volume)

    def test_handle_share_created_passes_a_share(self):
        """Test handle_VOLUME_CREATED parameter passing."""
        self.volume = None

        def a_callback(vol):
            setattr(self, 'volume', vol)

        self.client.set_volume_created_callback(a_callback)

        message = build_volume_created()
        set_share_message(message.volume_created)
        share = volumes.ShareVolume.from_msg(message.volume_created.share)

        self.client.handle_VOLUME_CREATED(message)
        self.assertEqual(share, self.volume)

    def test_handle_volume_created_if_callback_is_none(self):
        """Test handle_VOLUME_CREATED if callback is none."""
        message = build_volume_created()
        self.client.handle_VOLUME_CREATED(message)

    def test_handle_volume_deleted(self):
        """Test handle_VOLUME_DELETED."""
        a_callback = was_called(self, 'called')
        self.client.set_volume_deleted_callback(a_callback)

        message = build_volume_deleted()
        message.volume_deleted.volume = str(VOLUME)
        self.client.handle_VOLUME_DELETED(message)

        self.assertTrue(self.called)

    def test_handle_volume_deleted_passes_the_id(self):
        """Test handle_VOLUME_DELETED."""
        self.volume = None

        def a_callback(vol):
            setattr(self, 'volume', vol)

        self.client.set_volume_deleted_callback(a_callback)

        message = build_volume_deleted()
        message.volume_deleted.volume = str(VOLUME)
        self.client.handle_VOLUME_DELETED(message)

        self.assertEqual(VOLUME, self.volume)

    def test_handle_volume_deleted_if_none(self):
        """Test handle_VOLUME_DELETED if callback is none."""
        message = build_volume_deleted()
        self.client.handle_VOLUME_DELETED(message)


class RequestTestCase(TestCase):

    request_class = request.Request

    def make_request(self, *args, protocol=None, start=True, **kwargs):
        if protocol is None:
            protocol = FakedProtocol()
        request = self.request_class(protocol, *args, **kwargs)
        self.done_called = False
        request.deferred.addCallbacks(
            was_called(self, 'done_called'), faked_error)
        if start:
            request.start()
        return request


class CreateUDFTestCase(RequestTestCase):
    """Test cases for CreateUDF op."""

    request_class = CreateUDF

    @defer.inlineCallbacks
    def setUp(self):
        """Initialize testing protocol."""
        yield super(CreateUDFTestCase, self).setUp()
        self.request = self.make_request(path=PATH, name=NAME)

    def test_init(self):
        """Test request creation."""
        self.assertEqual(PATH, self.request.path)
        self.assertEqual(NAME, self.request.name)
        self.assertTrue(self.request.volume_id is None)
        self.assertTrue(self.request.node_id is None)

    def test_start(self):
        """Test request start."""
        request = self.make_request('path', 'name', start=False)

        request.start()

        self.assertEqual(1, len(request.protocol.messages))
        actual_msg, = request.protocol.messages
        self.assertEqual(protocol_pb2.Message.CREATE_UDF, actual_msg.type)
        self.assertEqual(request.path, actual_msg.create_udf.path)
        self.assertEqual(request.name, actual_msg.create_udf.name)

    @defer.inlineCallbacks
    def test_process_message_error(self):
        """Test request processMessage on error."""
        message = protocol_pb2.Message()
        self.request.processMessage(message)
        with self.assertRaises(FakedError):
            yield self.request.deferred

    def test_process_message_volume_created(self):
        """Test request processMessage on sucess."""
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.VOLUME_CREATED
        message.volume_created.type = protocol_pb2.Volumes.UDF
        message.volume_created.udf.volume = str(VOLUME)
        message.volume_created.udf.node = str(NODE)
        self.request.processMessage(message)

        self.assertEqual(str(VOLUME), self.request.volume_id, 'volume set')
        self.assertEqual(str(NODE), self.request.node_id, 'node set')
        self.assertTrue(self.done_called, 'done() was called')


class ListVolumesTestCase(RequestTestCase):
    """Test cases for ListVolumes op."""

    request_class = ListVolumes

    @defer.inlineCallbacks
    def setUp(self):
        """Initialize testing protocol."""
        yield super(ListVolumesTestCase, self).setUp()
        self.request = self.make_request()

    def test_init(self):
        """Test request creation."""
        self.assertEqual([], self.request.volumes)

    def test_start(self):
        """Test request start."""
        request = self.make_request(start=False)

        request.start()

        self.assertEqual(1, len(request.protocol.messages))
        actual_msg, = request.protocol.messages
        self.assertEqual(protocol_pb2.Message.LIST_VOLUMES, actual_msg.type)

    @defer.inlineCallbacks
    def test_process_message_error(self):
        """Test request processMessage on error."""
        message = protocol_pb2.Message()
        self.request.processMessage(message)
        with self.assertRaises(FakedError):
            yield self.request.deferred

    def test_process_message_volume_created(self):
        """Test request processMessage on sucess."""
        message = build_list_volumes()
        set_udf_message(message.list_volumes)
        udf = volumes.UDFVolume.from_msg(message.list_volumes.udf)
        self.request.processMessage(message)

        message = build_list_volumes()
        set_share_message(message.list_volumes)
        share = volumes.ShareVolume.from_msg(message.list_volumes.share)
        self.request.processMessage(message)

        message = build_list_volumes()
        set_root_message(message.list_volumes)
        root = volumes.RootVolume.from_msg(message.list_volumes.root)
        self.request.processMessage(message)

        self.assertEqual(3, len(self.request.volumes), '3 volumes stored')
        self.assertEqual([udf, share, root], self.request.volumes,
                         'volumes stored')

        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.VOLUMES_END
        self.request.processMessage(message)

        self.assertTrue(self.done_called, 'done() was called')

    def test_start_cleanups_volumes(self):
        """Test start() is idempotent."""
        request = self.make_request(start=False)

        request.start()

        message = build_list_volumes()
        set_udf_message(message.list_volumes)
        request.processMessage(message)

        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.VOLUMES_END
        request.processMessage(message)

        request.start()
        self.assertEqual([], request.volumes)


class DeleteVolumeTestCase(RequestTestCase):
    """Test cases for DeleteVolume op."""

    request_class = DeleteVolume

    @defer.inlineCallbacks
    def setUp(self):
        """Initialize testing protocol."""
        yield super(DeleteVolumeTestCase, self).setUp()
        self.request = self.make_request(volume_id=VOLUME)

    def test_init(self):
        """Test request creation."""
        self.assertEqual(str(VOLUME), self.request.volume_id)

    def test_start(self):
        """Test request start."""
        request = self.make_request('volume_id', start=False)

        request.start()

        self.assertEqual(1, len(request.protocol.messages))
        actual_msg, = request.protocol.messages
        self.assertEqual(protocol_pb2.Message.DELETE_VOLUME, actual_msg.type)
        self.assertEqual(
            request.volume_id, actual_msg.delete_volume.volume)

    @defer.inlineCallbacks
    def test_process_message_error(self):
        """Test request processMessage on error."""
        message = protocol_pb2.Message()
        self.request.processMessage(message)
        with self.assertRaises(FakedError):
            yield self.request.deferred

    def test_process_message_ok(self):
        """Test request processMessage on sucess."""
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.OK
        self.request.processMessage(message)

        self.assertTrue(self.done_called, 'done() was called')


class GetDeltaTestCase(RequestTestCase):
    """Test cases for GetDelta op."""

    request_class = GetDelta

    @defer.inlineCallbacks
    def setUp(self):
        """Initialize testing protocol."""
        yield super(GetDeltaTestCase, self).setUp()
        self.request = self.make_request(SHARE, 0)

    def test_init(self):
        """Test request creation."""
        self.assertEqual(str(SHARE), self.request.share_id)

    def test_start(self):
        """Test request start."""
        request = self.make_request('share_id', from_scratch=True, start=False)

        request.start()

        self.assertEqual(1, len(request.protocol.messages))
        actual_msg, = request.protocol.messages
        self.assertEqual(protocol_pb2.Message.GET_DELTA, actual_msg.type)
        self.assertEqual(request.share_id, actual_msg.get_delta.share)

    @defer.inlineCallbacks
    def test_process_message_error(self):
        """Test request processMessage on error."""
        message = protocol_pb2.Message()
        self.request.processMessage(message)
        with self.assertRaises(FakedError):
            yield self.request.deferred

    def test_process_message_ok(self):
        """Test request processMessage on sucess."""
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.DELTA_END
        message.delta_end.generation = 100
        message.delta_end.full = True
        message.delta_end.free_bytes = 200
        self.request.processMessage(message)

        self.assertTrue(self.done_called, 'done() was called')
        self.assertEqual(self.request.end_generation,
                         message.delta_end.generation)
        self.assertEqual(self.request.full, message.delta_end.full)
        self.assertEqual(self.request.free_bytes,
                         message.delta_end.free_bytes)

    def test_process_message_content(self):
        """Test request processMessage for content."""
        message = test_delta_info.get_message()
        self.request.processMessage(message)
        self.assertTrue(delta.from_message(message) in self.request.response)

    def test_process_message_content_twice(self):
        """Test request processMessage for content."""
        message = test_delta_info.get_message()
        self.request.processMessage(message)
        message = test_delta_info.get_message()
        self.request.processMessage(message)
        self.assertEqual(len(self.request.response), 2)

    def test_process_message_content_callback(self):
        """Test request processMessage for content w/callback."""
        response = []
        self.request = self.make_request(SHARE, 0, callback=response.append)
        message = test_delta_info.get_message()
        self.request.processMessage(message)
        self.assertTrue(delta.from_message(message) in response)

    def test_from_scratch_flag(self):
        """Test from scratch flag."""
        request = self.make_request(SHARE, 0, from_scratch=True, start=False)

        request.start()

        self.assertEqual(1, len(request.protocol.messages))
        actual_msg, = request.protocol.messages
        self.assertEqual(protocol_pb2.Message.GET_DELTA, actual_msg.type)
        self.assertEqual(request.share_id, actual_msg.get_delta.share)


class TestAuth(RequestTestCase):
    """Tests the authentication request."""

    request_class = Authenticate

    def test_session_id(self):
        """Test that the request has the session id attribute."""
        SESSION_ID = "opaque_session_id"
        req = self.make_request({})
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.AUTH_AUTHENTICATED
        message.session_id = SESSION_ID
        req.processMessage(message)
        self.assertTrue(self.done_called)
        self.assertEqual(req.session_id, SESSION_ID)

    def test_with_metadata(self):
        """Test with optional metadata."""
        protocol = FakedProtocol()
        protocol.dummy_authenticate('my_token',
                                    metadata={'version': '0.1',
                                              'platform': sys.platform})
        msgs = protocol.messages
        self.assertTrue(len(msgs), 1)
        msg = msgs[0]
        self.assertEqual(len(msg.auth_parameters), 1)
        self.assertEqual(len(msg.metadata), 2)
        metadata = {'version': '0.1', 'platform': sys.platform}
        for md in msg.metadata:
            self.assertTrue(md.key in metadata)
            self.assertEqual(md.value, metadata[md.key])

    def test_without_metadata(self):
        """Test without optional metadata."""
        protocol = FakedProtocol()
        protocol.dummy_authenticate('my_token')
        msgs = protocol.messages
        self.assertTrue(len(msgs), 1)
        msg = msgs[0]
        self.assertEqual(len(msg.auth_parameters), 1)
        self.assertEqual(len(msg.metadata), 0)


class RootResource(resource.Resource):
    """A root resource that logs the number of calls."""

    isLeaf = True

    def __init__(self, *args, **kwargs):
        """Initialize this fake instance."""
        self.count = 0
        self.request_headers = []

    def render_HEAD(self, request):
        """Increase the counter on each render."""
        self.request_headers.append(request.requestHeaders)
        self.count += 1
        return ""


class MockWebServer(object):
    """A mock webserver for testing."""

    def __init__(self):
        """Start up this instance."""
        self.root = RootResource()
        site = server.Site(self.root)
        application = service.Application('web')
        self.service_collection = service.IServiceCollection(application)
        self.tcpserver = internet.TCPServer(0, site)
        self.tcpserver.setServiceParent(self.service_collection)
        self.service_collection.startService()

    def get_url(self):
        """Build the url for this mock server."""
        port_num = self.tcpserver._port.getHost().port
        return "http://localhost:%d/" % port_num

    def stop(self):
        """Shut it down."""
        self.service_collection.stopService()


class TestGenerationInRequests(RequestTestCase):
    """Base class for testing that actions that change the volume will
    have a new_generation attribute set."""

    request_class = MakeFile

    def build_request(self):
        """Creates the request object."""
        return self.make_request("share", "parent_id", "name")

    def build_message(self):
        """Creates the ending message for the request."""
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.NEW_FILE
        message.new_generation = GENERATION
        return message

    def test_make(self):
        """Test the request for new_generation."""
        req = self.build_request()
        message = self.build_message()
        req.processMessage(message)
        self.assertTrue(self.done_called)
        self.assertEqual(req.new_generation, GENERATION)


class TestGenerationInRequestsMakeDir(TestGenerationInRequests):
    """Tests for new_generation in MakeDir."""

    request_class = MakeDir

    def build_message(self):
        """Creates the ending message for the request."""
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.NEW_DIR
        message.new_generation = GENERATION
        return message


class TestGenerationInRequestsPutContent(TestGenerationInRequests):
    """Tests for new_generation in PutContent."""

    request_class = PutContent

    def build_request(self):
        """Creates the request object."""
        return self.make_request(
            'share', 'node', 'previous_hash', 'new_hash', 123, 456, 789, 'fd')

    def build_message(self):
        """Creates the ending message for the request."""
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.OK
        message.new_generation = GENERATION
        return message


class TestGenerationInRequestsUnlink(TestGenerationInRequestsPutContent):
    """Tests for new_generation in Unlink."""

    request_class = Unlink

    def build_request(self):
        """Creates the request object."""
        return self.make_request('share', 'node')


class TestGenerationInRequestsMove(TestGenerationInRequestsPutContent):
    """Tests for new_generation in Move."""

    request_class = Move

    def build_request(self):
        """Creates the request object."""
        return self.make_request('share', 'node', 'new_parent', 'new_name')


class PutContentTestCase(RequestTestCase):
    """Test cases for PutContent op."""

    request_class = PutContent

    def build_request(self, protocol=None):
        """Creates the request object."""
        return self.make_request(
            'share', 'node', 'previous_hash', 'new_hash', 123, 456, 789, 'fd',
            protocol=protocol)

    def test_max_payload_size(self):
        """Get the value from the protocol."""
        protocol = FakedProtocol()
        assert 12345 != protocol.max_payload_size
        protocol.max_payload_size = 12345
        pc = self.build_request(protocol)
        self.assertEqual(pc.max_payload_size, 12345)

    def test_bytesmessageproducer_maxpayloadsize(self):
        """The producer uses the payload size from the request."""
        pc = self.build_request()
        assert 12 != pc.max_payload_size
        pc.max_payload_size = 12

        # set up the producer with a content with size 19
        fake_file = io.BytesIO(b"some binary content")
        producer = BytesMessageProducer(pc, fake_file, 0)
        producer.producing = True

        producer.go()
        self.assertEqual(fake_file.tell(), 12)


class ChangePublicAccessTestCase(RequestTestCase):
    """Test cases for ChangePublicAccess op."""

    request_class = ChangePublicAccess

    @defer.inlineCallbacks
    def setUp(self):
        """Initialize testing protocol."""
        yield super(ChangePublicAccessTestCase, self).setUp()
        self.request = self.make_request(
            share_id=SHARE, node_id=NODE, is_public=True)

    def test_init(self):
        """Test request creation."""
        self.assertEqual(self.request.share_id, str(SHARE))
        self.assertEqual(self.request.node_id, str(NODE))
        self.assertTrue(self.request.is_public)

    def test_start(self):
        """Test request start."""
        request = self.make_request(
            share_id=SHARE, node_id=NODE, is_public=True, start=False)

        request.start()

        self.assertEqual(1, len(request.protocol.messages))
        actual_msg, = request.protocol.messages
        self.assertEqual(
            actual_msg.type, protocol_pb2.Message.CHANGE_PUBLIC_ACCESS)
        self.assertEqual(
            actual_msg.change_public_access.share, request.share_id)
        self.assertEqual(
            actual_msg.change_public_access.node, request.node_id)
        self.assertTrue(actual_msg.change_public_access.is_public)

    @defer.inlineCallbacks
    def test_process_message_error(self):
        """Test request processMessage on error."""
        message = protocol_pb2.Message()
        self.request.processMessage(message)
        with self.assertRaises(FakedError):
            yield self.request.deferred
        self.assertIsNone(self.request.public_url)

    def test_process_message_ok(self):
        """Test request processMessage on sucess."""
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.OK
        message.public_url = PUBLIC_URL
        self.request.processMessage(message)

        self.assertTrue(self.done_called, 'done() was called')
        self.assertIsNotNone(self.request.public_url)


class ListPublicFilesTestCase(RequestTestCase):
    """Test cases for ListPublicFiles op."""

    request_class = ListPublicFiles

    @defer.inlineCallbacks
    def setUp(self):
        """Initialize testing protocol."""
        yield super(ListPublicFilesTestCase, self).setUp()
        self.request = self.make_request()

    def test_start(self):
        """Test request start."""
        request = self.make_request(start=False)

        request.start()

        self.assertEqual(1, len(request.protocol.messages))
        actual_msg, = request.protocol.messages
        self.assertEqual(
            actual_msg.type, protocol_pb2.Message.LIST_PUBLIC_FILES)

    @defer.inlineCallbacks
    def test_process_message_error(self):
        """Test request processMessage on error."""
        message = protocol_pb2.Message()
        self.request.processMessage(message)
        with self.assertRaises(FakedError):
            yield self.request.deferred
        self.assertEqual(self.request.public_files, [])

    def test_process_message_ok(self):
        """Test request processMessage on sucess."""
        # send two nodes
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.PUBLIC_FILE_INFO
        message.public_file_info.share = 'share_id'
        message.public_file_info.node = 'node_id_1'
        message.public_file_info.is_public = True
        message.public_file_info.public_url = "test url 123"
        self.request.processMessage(message)

        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.PUBLIC_FILE_INFO
        message.public_file_info.share = 'share_id'
        message.public_file_info.node = 'node_id_2'
        message.public_file_info.is_public = True
        message.public_file_info.public_url = "test url 456"
        self.request.processMessage(message)

        # finish
        message = protocol_pb2.Message()
        message.type = protocol_pb2.Message.PUBLIC_FILE_INFO_END
        self.request.processMessage(message)

        # check
        self.assertTrue(self.done_called, 'done() was called')
        node1, node2 = self.request.public_files

        self.assertEqual(node1.share_id, 'share_id')
        self.assertEqual(node1.node_id, 'node_id_1')
        self.assertEqual(node1.is_public, True)
        self.assertEqual(node1.public_url, 'test url 123')

        self.assertEqual(node2.share_id, 'share_id')
        self.assertEqual(node2.node_id, 'node_id_2')
        self.assertEqual(node2.is_public, True)
        self.assertEqual(node2.public_url, 'test url 456')
