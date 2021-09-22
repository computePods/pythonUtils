import asyncio
import unittest

from cputils.settlingTimerMixin import mixinSettlingTimer
from cputils.natsClient import NatsClient
from tests.testUtils import asyncTestOfProcess

class SimpleObject :
  pass

class TestSettlingTimerMixin(unittest.TestCase) :

  async def settlingTimerCallback(t) :
    t.timerCalled = True

  @asyncTestOfProcess(None)
  async def test_settlingTimerOnClass(t) :
    """Test the settling timer, monkey patched onto the instance of a
    class, to ensure repeated calls to the unSettle method keeps the timer
    going (and the object unsettled). """

    nc = NatsClient("settlingTimerMixin_Tests", 1)
    t.assertIsNotNone(nc)
    await nc.connectToServers(["nats://localhost:8888"])

    obj = SimpleObject()
    t.assertIsNotNone(obj)
    mixinSettlingTimer(obj, 0.03, t.settlingTimerCallback)
    t.timerCalled = False
    t.assertIsNotNone(obj)
    t.assertTrue(hasattr(obj, 'hasSettled'))
    t.assertTrue(hasattr(obj, 'unSettle'))
    t.assertTrue(hasattr(obj, 'waitUntilSettled'))
    t.assertTrue(hasattr(obj, 'addSettlingTimer'))
    t.assertTrue(obj.hasSettled())
    t.assertFalse(t.timerCalled)
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertFalse(obj.hasSettled())
    t.assertFalse(t.timerCalled)
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertFalse(obj.hasSettled())
    t.assertFalse(t.timerCalled)
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertFalse(obj.hasSettled())
    t.assertFalse(t.timerCalled)
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertFalse(obj.hasSettled())
    t.assertFalse(t.timerCalled)
    await obj.unSettle()
    await asyncio.sleep(0.01)
    t.assertFalse(obj.hasSettled())
    t.assertFalse(t.timerCalled)
    await obj.waitUntilSettled()
    t.assertTrue(obj.hasSettled())
    t.assertTrue(t.timerCalled)

    obj.addSettlingTimer('timer', 0.3)
    t.assertTrue(obj.hasSettled('timer'))
    await obj.unSettle('timer')
    await asyncio.sleep(0.01)
    t.assertFalse(obj.hasSettled('timer'))
    await obj.waitUntilSettled('timer')
    t.assertTrue(obj.hasSettled('timer'))

    t.assertTrue(obj.hasSettled('noTimer'))
    await obj.unSettle('noTimer')
    await asyncio.sleep(0.01)
    t.assertTrue(obj.hasSettled('noTimer'))
    await obj.waitUntilSettled('noTimer')
    t.assertTrue(obj.hasSettled('noTimer'))
