import asyncio
import os
import unittest

from cputils.natsClient import NatsClient
from cputils.natsListener import ( natsListener,
  filterSubjects, messageCollector,
   hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestNatsListener(unittest.TestCase) :

  def testFiterSubjects(t) :
    """Ensure the `filterSubjects` method can filter on the various filter
    methods."""

    t.assertIsNone(filterSubjects(None))
    t.assertIsNone(filterSubjects([]))
    t.assertIsNone(filterSubjects(['a.subject'], 'noMethod'))

    aFilter = filterSubjects(['a.subject'])
    t.assertIsNotNone(aFilter)
    t.assertTrue(aFilter('a.subject', ''))
    t.assertFalse(aFilter('', 'a.subject'))
    t.assertFalse(aFilter('not.a.subject', ''))

    aFilter = filterSubjects(['a.subject'], 'equals')
    t.assertIsNotNone(aFilter)
    t.assertTrue(aFilter('a.subject', ''))
    t.assertFalse(aFilter('', ''))
    t.assertFalse(aFilter('not.a.subject', ''))

    aFilter = filterSubjects(['a.sub', 'not.a.sub'], 'startsWith')
    t.assertIsNotNone(aFilter)
    t.assertTrue(aFilter('a.subject', ''))
    t.assertTrue(aFilter('not.a.subject', ''))
    t.assertFalse(aFilter('still.not.a.subject', ''))

  @asyncTestOfProcess()
  async def testMessageCollector(t) :
    """Ensure the message collector can collect NATS messages."""

    t.assertIsNone(messageCollector(None))
    t.assertIsNone(messageCollector('notADict'))

    aMessageCollection = {}
    aCollector = messageCollector(aMessageCollection)
    t.assertIsNotNone(aCollector)
    await aCollector('a.subject', 'the.subject', 'a.subject (the.subject) message1')
    await aCollector('a.subject', 'the.subject', 'a.subject (the.subject) message2')
    await aCollector('a.subject', 'the.subject', 'a.subject (the.subject) message3')
    t.assertTrue('the.subject' in aMessageCollection)
    t.assertTrue(hasMessage(aMessageCollection, 'the.subject'))
    t.assertFalse(hasMessage(aMessageCollection, 'not.the.subject'))
    t.assertEqual(len(aMessageCollection['the.subject']), 3)
    t.assertTrue(hasMessage(aMessageCollection, 'the.subject', 'a.subject (the.subject) message1'))
    t.assertTrue(hasMessage(aMessageCollection, 'the.subject', 'a.subject (the.subject) message2'))
    t.assertTrue(hasMessage(aMessageCollection, 'the.subject', 'a.subject (the.subject) message3'))
    t.assertFalse(hasMessage(aMessageCollection, 'the.subject', 'a.subject (the.subject) message4'))
    t.assertEqual(len(getMessages(aMessageCollection)), 3)
    t.assertEqual(numMessages(aMessageCollection), 3)
    t.assertEqual(len(getMessages(aMessageCollection, 'the.subject')), 3)
    t.assertEqual(numMessages(aMessageCollection, 'the.subject'), 3)
    t.assertEqual(len(getMessages(aMessageCollection, 'not.the.subject')), 0)
    t.assertEqual(numMessages(aMessageCollection, 'not.the.subject'), 0)
    someMessages = getMessages(aMessageCollection, 'the.subject')
    aMessage = someMessages[1]
    t.assertTrue('aSubject' in aMessage)
    t.assertEqual(aMessage['aSubject'], 'the.subject')
    t.assertTrue('aMessage' in aMessage)
    t.assertEqual(aMessage['aMessage'], 'a.subject (the.subject) message2')

  @asyncTestOfProcess()
  async def testNatsListener(t) :
    """Ensure that the end-to-end NATS message collection works using the
    `natsListener`. Test using the `hasMessage`, `getMessages`, and
    `numMessages` tools."""

    nc = NatsClient("natsListener_Tests", 1)
    await nc.connectToServers([
      os.getenv('NATS_SERVER', "nats://localhost:8888")
    ])

    # Test while listening to ALL messages
    aMessageCollection = {}
    await natsListener(nc, messageCollector(aMessageCollection))
    t.assertEqual(numMessages(aMessageCollection), 0)
    await nc.sendMessage('test.send.and.listen', "This is a natsListener test!")
    t.assertEqual(numMessages(aMessageCollection), 1)
    t.assertEqual(numMessages(aMessageCollection, 'test.send.and.listen'), 1)
    t.assertTrue(hasMessage(aMessageCollection, 'test.send.and.listen'))
    t.assertTrue(hasMessage(aMessageCollection, 'test.send.and.listen', "This is a natsListener test!"))

    # Test while listening only to 'test.>' messages
    aMessageCollection = {}
    await natsListener(nc, messageCollector(aMessageCollection), 'test.>')
    t.assertEqual(numMessages(aMessageCollection), 0)
    await nc.sendMessage('test.send.and.listen', "This is a natsListener test!")
    t.assertEqual(numMessages(aMessageCollection), 1)
    t.assertEqual(numMessages(aMessageCollection, 'test.send.and.listen'), 1)
    t.assertTrue(hasMessage(aMessageCollection, 'test.send.and.listen'))
    t.assertTrue(hasMessage(aMessageCollection, 'test.send.and.listen', "This is a natsListener test!"))

    # Test while listening only to 'not.a.test.>' messages
    # (should NOT collect any messages)
    aMessageCollection = {}
    await natsListener(nc, messageCollector(aMessageCollection), 'not.a.test.>')
    t.assertEqual(numMessages(aMessageCollection), 0)
    await nc.sendMessage('test.send.and.listen', "This is a natsListener test!")
    t.assertEqual(numMessages(aMessageCollection), 0)
    t.assertEqual(numMessages(aMessageCollection, 'test.send.and.listen'), 0)
    t.assertFalse(hasMessage(aMessageCollection, 'test.send.and.listen'))
    t.assertFalse(hasMessage(aMessageCollection, 'test.send.and.listen', "This is a natsListener test!"))
