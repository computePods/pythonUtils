import asyncio
import os
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

  @asyncTestOfProcess(None)
  async def test_listenForTypes(t) :
    """Test the TypesManager's ability to listen for types messages."""

    nc = NatsClient("typesListener", 10)
    await nc.connectToServers([
      os.getenv('NATS_SERVER', "nats://localhost:8888")
    ])

    tm = TypesManager(nc)
    await tm.listenForTypeMessages()

    typesCollection = SettlingDict(timeOut=0.3)
    await natsListener(
      nc, messageCollector(typesCollection),
      'registered.types'
    )
    rulesCollection = SettlingDict(timeOut=0.3)
    await natsListener(
      nc, messageCollector(rulesCollection),
      'registered.rules'
    )

    rm = RulesManager('listenForTypes', nc)
    rm.loadRulesFrom('examples/rulesManager/workingRules')
    await rm.registerRules()
    await asyncio.sleep(1)
    await tm.waitUntilSettled('typeRegistration')

    t.assertEqual(len(tm.getTypeNames()), 10)
    typeNames = tm.getTypeNames()
    t.assertIn('applicationFile', typeNames)
    t.assertIn('cCodeFile', typeNames)
    t.assertIn('cHeaderFile', typeNames)
    t.assertIn('cObjectFile', typeNames)
    t.assertIn('cSharedLibFile', typeNames)
    t.assertIn('cStaticLibFile', typeNames)
    t.assertIn('contextDocument', typeNames)
    t.assertIn('htmlFile', typeNames)
    t.assertIn('luaFile', typeNames)
    t.assertIn('pdfFile', typeNames)

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
    t.assertEqual(len(tm.types), 10)

    # make sure that the artefact manager sends out a list of all
    # registered types

    await asyncio.sleep(1)
    await typesCollection.waitUntilSettled()
    t.assertTrue('registered.types' in typesCollection)
    t.assertTrue(len(typesCollection['registered.types']), 1)
    t.assertEqual(
      typesCollection['registered.types'][0],
      ['applicationFile',
       'cCodeFile', 'cHeaderFile', 'cObjectFile',
       'cSharedLibFile', 'cStaticLibFile',
       'contextDocument', 'htmlFile', 'luaFile', 'pdfFile'
      ]
    )

    await tm.waitUntilSettled('ruleRegistration')
    testRules = {
      'pdf2html' : {
        "dependencies": [ "pdfFile" ],
        "outputs": [ "htmlFile" ]
      },
      'objectFiles' : {
        "dependencies": [
          "cCodeFile",
          "cHeaderFile"
        ],
        "outputs": [ "cObjectFile" ]
      },
      'staticLibraries' : {
        "dependencies": [
          "cObjectFile",
          "cStaticLibFile"
        ],
        "outputs": [ "cStaticLibFile" ]
      },
      'sharedLibraries' : {
        "dependencies": [
          "cObjectFile",
          "cStaticLibFile",
          "cSharedLibFile"
        ],
        "outputs": [ "cSharedLibFile" ]
      },
      'applications' : {
        "dependencies": [
          "cObjectFile",
          "cStaticLibFile",
          "cSharedLibFile"
        ],
        "outputs": [ "applicationFile" ]
      },
      'context' : {
        "dependencies": [
          "contextDocument",
          "luaFile"
         ],
        "outputs": [
          "pdfFile",
          "luaFile",
          "cCodeFile",
          "cHeaderFile"
        ],
        "secondaryDependencies": [ "luaFile" ]
      },
    }
    for ruleName in testRules :
      t.assertIn(ruleName, tm.rules)
      theRule = tm.rules[ruleName]
      for testKey in testRules[ruleName] :
        t.assertIn(testKey, theRule)
        for testValue in testRules[ruleName][testKey] :
          t.assertIn(testValue, theRule[testKey])
          t.assertIn('listenForTypes', theRule[testKey][testValue])

    tm.createTupGraphDot('/tmp/typesTupGraph.dot')
