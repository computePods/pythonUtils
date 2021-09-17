import asyncio
import os
import shutil
import unittest
from unittest.mock import patch
import yaml

from cputils.natsClient import NatsClient
from tests.testUtils import asyncTestOfProcess

class TestNatsClient(unittest.TestCase):
  """ Test the NATS client. """

  @asyncTestOfProcess()
  async def testSendAndListen(t) :
    """Ensure the natsClient can both send and listen to NATS messages."""

    nc = NatsClient("natsClient_Tests", 1)
    await nc.connectToServers(["nats://localhost:8888"])
    def aCallback(aSubject, theSubject, aNATSMessage) :
      try:
        t.assertEqual(aSubject, "test.send.and.listen")
        t.assertEqual(theSubject, "test.send.and.listen")
        t.assertEqual(aNATSMessage, "This is a natsClient test!")
        t.asyncTestFuture.set_result(None)
      except Exception as err :
        t.asyncTestFuture.set_exception(err)
    await nc.listenToSubject('test.send.and.listen', aCallback)
    await nc.sendMessage('test.send.and.listen', "This is a natsClient test!")
    await nc.closeConnection()

  @asyncTestOfProcess()
  async def testHeartBeats(t) :
    """Ensure the natsClient can manage heartBeat messages for a
    process."""

    nc = NatsClient("natsClient_Tests", 1)
    await nc.connectToServers(["nats://localhost:8888"])
    numHeartBeats = [] # We use an array since it is 'passed' as a reference
    def aCallback(aSubject, theSubject, aNATSMessage) :
      numHeartBeats.append("newHeartBeat")
      if 2 < len(numHeartBeats) :
        nc.stopHeartBeat()
        t.asyncTestFuture.set_result(None)
      try:
        t.assertEqual(aSubject, "heartbeat")
        t.assertEqual(theSubject, "heartbeat")
        t.assertRegex(aNATSMessage, "hello from nn01-natsClient_Tests")
      except Exception as err :
        t.asyncTestFuture.set_exception(err)
    await nc.listenToSubject('heartbeat', aCallback)
    await asyncio.create_task(nc.heartBeat())
    await nc.closeConnection()
