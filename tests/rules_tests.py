import asyncio
import shutil
import unittest
from unittest.mock import patch
import yaml

import inspect

from cputils.natsClient import NatsClient
from cputils.yamlLoader import NoYamlFile, NoYamlDirectory
from cputils.rulesManager import RulesManager
from cputils.settlingTimerMixin import SettlingDict
from cputils.natsListener import ( natsListener, messageCollector,
  hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestRulesManager(unittest.TestCase):
  """ Test the Rules Manager. """

  @patch('cputils.yamlLoader.logging')
  def test_loadRulesWithNoDir(t, mock_logging) :
    """Test loading rules from a directory which does not exist"""

    rm = RulesManager('loadRulesWithNoDir', None)
    with t.assertRaises(NoYamlDirectory) as nrd :
      rm.loadRulesFrom("/this/directory/does/not/exist")
    t.assertEqual(nrd.exception.yamlPath, "/this/directory/does/not/exist")
    mock_logging.error.assert_called_with(
      'No YAML directory found at [/this/directory/does/not/exist]'
    )

  @patch('cputils.yamlLoader.logging')
  def test_loadRulesWithBrokenYaml(t, mock_logging) :
    """Test loading rules from a broken YAML file"""

    rm = RulesManager('loadRulesWithBrokenYaml', None)
    with t.assertRaises(NoYamlFile) as nrf :
      rm.loadRulesFrom("examples/rulesManagerBroken")
    t.assertEqual(nrf.exception.yamlPath, "examples/rulesManagerBroken/shouldNotLoad.yaml")
    t.assertRegex(nrf.exception.message, r"ScannerError.*mapping values")
    t.assertRegex(
      repr(mock_logging.error.call_args_list),
      r"ScannerError.*mapping values"
    )

  @patch('cputils.yamlLoader.logging')
  def test_loadRules(t, mock_logging) :
    """ When loading a rule set... """

    rm = RulesManager('loadRules', None)
    rm.loadRulesFrom('examples/rulesManager')
    t.assertNotEqual(rm, {})
    t.assertIn('types', rm.rulesData)
    t.assertIn('cCodeFile', rm.rulesData['types'])
    t.assertIn('extensions', rm.rulesData['types']['cCodeFile'])
    t.assertEqual(rm.rulesData['types']['cCodeFile']['extensions'][0], '*.c')

  ##########################################################################
  # Registering Artefact Types

  @asyncTestOfProcess(None)
  async def test_registerRules(t) :
    """ Make sure that any new Artefact types are sent to the
    ArtefactManager via NATS. """

    nc = NatsClient("natsTypesListener", 10)
    await nc.connectToServers(["nats://localhost:8888"])

    typesCollection = SettlingDict(timeOut=0.3)
    rulesCollection = SettlingDict(timeOut=0.3)

    await natsListener(
      nc, messageCollector(typesCollection),
      'register.types'
    )
    await natsListener(
      nc, messageCollector(rulesCollection),
      'register.rules'
    )

    rm = RulesManager('registerRules', nc)
    rm.loadRulesFrom('examples/rulesManager')
    await rm.registerRules()
    await asyncio.sleep(1)
    await typesCollection.waitUntilSettled()
    t.assertEqual(len(typesCollection), 1)
    t.assertTrue('register.types' in typesCollection)
    registeredTypes = {
      'applicationFile' :  [ ],
      'cCodeFile'       :  [ "*.c" ],
      'cHeaderFile'     :  [ "*.h" ],
      'cObjectFile'     :  [ "*.o" ],
      'cSharedLibFile'  :  [ "*.so" ],
      'cStaticLibFile'  :  [ "*.a" ],
      'contextDocument' :  [ "*.tex" ],
      'htmlFile'        :  [ "*.html", '*.htm' ],
      'luaFile'         :  [ "*.lua" ],
      'pdfFile'         :  [ "*.pdf" ],
    }
    msgs = typesCollection['register.types']
    t.assertEqual(len(msgs), len(registeredTypes))
    for aMsg in msgs :
      t.assertTrue('typeName' in aMsg)
      typeName = aMsg['typeName']
      t.assertTrue(typeName in registeredTypes)
      t.assertTrue('extensions' in aMsg)
      t.assertEqual(aMsg['extensions'], registeredTypes[typeName])
      t.assertTrue('chefName' in aMsg)
      t.assertEqual(aMsg['chefName'], 'registerRules')

    await rulesCollection.waitUntilSettled()
    testRules = {
      'pdf2html' : {
        "chefName": "registerRules",
        "ruleName": "pdf2html",
        "theRule": {
          "dependencies": [ "pdfFile" ],
          "outputs": [ "htmlFile" ]
        }
      },
      'objectFiles' : {
        "chefName": "registerRules",
        "ruleName": "objectFiles",
        "theRule": {
          "dependencies": [
            "cCodeFile",
            "cHeaderFile"
          ],
          "outputs": [ "cObjectFile" ]
        }
      },
      'staticLibraries' : {
        "chefName": "registerRules",
        "ruleName": "staticLibraries",
        "theRule": {
          "dependencies": [
            "cObjectFile",
            "cStaticLibFile"
          ],
          "outputs": [ "cStaticLibFile" ]
        }
      },
      'sharedLibraries' : {
        "chefName": "registerRules",
        "ruleName": "sharedLibraries",
        "theRule": {
          "dependencies": [
            "cObjectFile",
            "cStaticLibFile",
            "cSharedLibFile"
          ],
          "outputs": [ "cSharedLibFile" ]
        }
      },
      'applications' : {
        "chefName": "registerRules",
        "ruleName": "applications",
        "theRule": {
          "dependencies": [
            "cObjectFile",
            "cStaticLibFile",
            "cSharedLibFile"
          ],
          "outputs": [ "applicationFile" ]
        }
      },
      'context' : {
        "chefName": "registerRules",
        "ruleName": "context",
        "theRule": {
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
        }
      },
    }
    t.assertTrue('register.rules' in rulesCollection)
    for aRule in rulesCollection['register.rules'] :
      t.assertIn('chefName', aRule)
      t.assertEqual(aRule['chefName'], 'registerRules')
      t.assertIn('ruleName', aRule)
      ruleName = aRule['ruleName']
      t.assertIn(ruleName, testRules)
      testRule = testRules[ruleName]
      t.assertIn('theRule', aRule)
      theRule = aRule['theRule']
      for testKey in testRule['theRule'] :
        t.assertIn(testKey, theRule)
        for testValue in theRule[testKey] :
          t.assertIn(testValue, testRule['theRule'][testKey], msg="testKey: {}".format(testKey))
        for testValue in testRule['theRule'][testKey] :
          t.assertIn(testValue, theRule[testKey])
      for testKey in aRule['theRule'] :
        t.assertIn(testKey, testRule['theRule'])
