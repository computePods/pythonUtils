import asyncio
import logging
import os
import shutil
import unittest
from unittest.mock import patch
import yaml

from cputils.natsClient import NatsClient
from cputils.natsListener import ( natsListener, messageCollector,
  hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestNatsClient(unittest.TestCase):
  """ Test the NATS client. """

  @asyncTestOfProcess()
  async def testSendAndListen(t) :
    """Ensure the natsClient can both send and listen to NATS messages."""

    nc = NatsClient("natsClient_Tests", 1)
    await nc.connectToServers(["nats://localhost:8888"])

    # Test using a manual callback so that we can test to ensure the
    # correct call pattern and values are honoured.
    def aCallback(aSubject, theSubject, aNATSMessage) :
      try:
        t.assertEqual(aSubject, "test.send.>")
        t.assertEqual(theSubject, "test.send.and.listen")
        t.assertEqual(aNATSMessage, "This is a natsClient test!")
        t.asyncTestFuture.set_result(None)
      except Exception as err :
        t.asyncTestFuture.set_exception(err)
    await nc.listenToSubject('test.send.>', aCallback)
    await nc.sendMessage('test.send.and.listen', "This is a natsClient test!")
    await nc.closeConnection()

  @asyncTestOfProcess()
  async def testHeartBeats(t) :
    """Ensure the natsClient can manage heartBeat messages for a
    process, and that we can stop the heartbeats when complete."""

    nc = NatsClient("natsClient_Tests", 0.1)
    await nc.connectToServers(["nats://localhost:8888"])
    aMessageCollection = {}
    await natsListener(nc, messageCollector(aMessageCollection), 'heartbeat')

    asyncio.create_task(nc.heartBeat())
    await asyncio.sleep(0.5)
    nc.stopHeartBeat()

    t.assertTrue(hasMessage(aMessageCollection, "heartbeat"))
    someMessages = getMessages(aMessageCollection, "heartbeat")
    t.assertGreater(len(someMessages), 2)
    t.assertRegex(someMessages[1]['aMessage'], "hello from nn01-natsClient_Tests")

    await nc.closeConnection()
