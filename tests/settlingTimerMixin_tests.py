import asyncio
import unittest

from cputils.settlingTimerMixin import mixinSettlingTimer
from cputils.natsClient import NatsClient
from cputils.natsListener import ( natsListener, messageCollector,
   hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class SimpleObject :
  pass

class TestSettlingTimerMixin(unittest.TestCase) :

  @asyncTestOfProcess(None)
  async def test_settlingTimer(t) :
    """Test the settling timer to ensure repeated calls to the unSettle
    method keeps the timer going (and the object unsettled). """

    nc = NatsClient("settlingTimerMixin_Tests", 1)
    t.assertIsNotNone(nc)
    await nc.connectToServers(["nats://localhost:8888"])

    aMessageCollection = {}
    await natsListener(nc, messageCollector(aMessageCollection), 'settled.tests')

    obj = SimpleObject()
    t.assertIsNotNone(obj)
    mixinSettlingTimer(obj, 0.03, nc, 'settled.tests')
    t.assertIsNotNone(obj)
    t.assertTrue(hasattr(obj, 'hasSettled'))
    t.assertTrue(hasattr(obj, 'unSettle'))
    t.assertTrue(obj.hasSettled())
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertEqual(numMessages(aMessageCollection), 0)
    t.assertFalse(obj.hasSettled())
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertEqual(numMessages(aMessageCollection), 0)
    t.assertFalse(obj.hasSettled())
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertEqual(numMessages(aMessageCollection), 0)
    t.assertFalse(obj.hasSettled())
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertEqual(numMessages(aMessageCollection), 0)
    t.assertFalse(obj.hasSettled())
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertEqual(numMessages(aMessageCollection), 0)
    t.assertFalse(obj.hasSettled())
    await asyncio.sleep(0.1)
    t.assertEqual(numMessages(aMessageCollection), 1)
    t.assertTrue(obj.hasSettled())
