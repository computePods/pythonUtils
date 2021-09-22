import asyncio
import unittest
import yaml

from cputils.natsClient import NatsClient

from cputils.typesManager import TypesManager
from cputils.rulesManager    import RulesManager

from cputils.settlingTimerMixin import SettlingDict
from cputils.natsListener import ( natsListener, messageCollector,
   hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestTypesManager(unittest.TestCase) :
  """Test the TypesManager"""

  def artefactTypeTests(t, am, name, extensions) :
    at = am.types
    t.assertTrue(name in at)
    aType = at[name]
    t.assertTrue('typeName' in aType)
    t.assertEqual(aType['typeName'], name)
    t.assertTrue('extensions' in aType)
    for anExtension in extensions :
      t.assertTrue(anExtension in aType['extensions'])
      t.assertEqual(aType['extensions'][anExtension], { 'listenForTypes' : True } )
    del at[name]

  @asyncTestOfProcess(None)
  async def test_listenForTypes(t) :
    """Test the TypesManager's ability to listen for types messages."""

    nc = NatsClient("typesListener", 10)
    await nc.connectToServers(["nats://localhost:8888"])

    tm = TypesManager(nc)
    await tm.listenForTypeMessages()

    msgCollection = SettlingDict(timeOut=0.3)
    await natsListener(
      nc, messageCollector(msgCollection),
      'types.registered'
    )

    rm = RulesManager('listenForTypes', nc)
    rm.loadRulesFrom('examples/rulesManager')
    await rm.registerTypes()
    await asyncio.sleep(1)
    await tm.waitUntilSettled('typeRegistration')

    t.assertEqual(len(tm.getTypeNames()), 10)
    typeNames = tm.getTypeNames()
    t.assertTrue('applicationFile' in typeNames)
    t.assertTrue('cCodeFile' in typeNames)
    t.assertTrue('cHeaderFile' in typeNames)
    t.assertTrue('cObjectFile' in typeNames)
    t.assertTrue('cSharedLibFile' in typeNames)
    t.assertTrue('cStaticLibFile' in typeNames)
    t.assertTrue('contextDocument' in typeNames)
    t.assertTrue('htmlFile' in typeNames)
    t.assertTrue('luaFile' in typeNames)
    t.assertTrue('pdfFile' in typeNames)

    t.artefactTypeTests(
      tm,
      'applicationFile',
      [ ]
    )
    t.artefactTypeTests(
      tm,
      'cCodeFile',
      [ "*.c" ]
    )
    t.artefactTypeTests(
      tm,
      'cHeaderFile',
      [ "*.h" ]
    )
    t.artefactTypeTests(
      tm,
      'cObjectFile',
      [ "*.o" ]
    )
    t.artefactTypeTests(
      tm,
      'cSharedLibFile',
      [ "*.so" ]
    )
    t.artefactTypeTests(
      tm,
      'cStaticLibFile',
      [ "*.a" ]
    )
    t.artefactTypeTests(
      tm,
      'contextDocument',
      [ "*.tex" ]
    )
    t.artefactTypeTests(
      tm,
      'htmlFile',
      [ "*.html", '*.htm' ]
    )
    t.artefactTypeTests(
      tm,
      'luaFile',
      [ "*.lua" ]
    )
    t.artefactTypeTests(
      tm,
      'pdfFile',
      [ "*.pdf" ]
    )
    t.assertEqual(len(tm.types), 0)

    # make sure that the artefact manager sends out a list of all
    # registered types

    await asyncio.sleep(1)
    await msgCollection.waitUntilSettled()
    t.assertTrue('types.registered' in msgCollection)
    t.assertTrue(len(msgCollection['types.registered']), 1)
    t.assertEqual(
      msgCollection['types.registered'][0],
      ['applicationFile',
       'cCodeFile', 'cHeaderFile', 'cObjectFile',
       'cSharedLibFile', 'cStaticLibFile',
       'contextDocument', 'htmlFile', 'luaFile', 'pdfFile'
      ]
    )
