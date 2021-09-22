import asyncio
import shutil
import unittest
from unittest.mock import patch
import yaml

import inspect

from cputils.natsClient import NatsClient
from cputils.rulesManager import RulesManager, NoRulesFile, NoRulesDirectory
from cputils.settlingTimerMixin import SettlingDict
from cputils.natsListener import ( natsListener, messageCollector,
  hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestRulesManager(unittest.TestCase):
  """ Test the Rules Manager. """

  @patch('cputils.rulesManager.logging')
  def test_loadRulesWithNoDir(t, mock_logging) :
    """Test loading rules from a directory which does not exist"""

    rm = RulesManager('loadRulesWithNoDir', None)
    with t.assertRaises(NoRulesDirectory) as nrd :
      rm.loadRulesFrom("/this/directory/does/not/exist")
    t.assertEqual(nrd.exception.rulesPath, "/this/directory/does/not/exist")
    mock_logging.error.assert_called_with(
      'No rules directory found at [/this/directory/does/not/exist]'
    )

  @patch('cputils.rulesManager.logging')
  def test_loadRulesWithBrokenYaml(t, mock_logging) :
    """Test loading rules from a broken YAML file"""

    rm = RulesManager('loadRulesWithBrokenYaml', None)
    with t.assertRaises(NoRulesFile) as nrf :
      rm.loadRulesFrom("examples/rulesManagerBroken")
    t.assertEqual(nrf.exception.rulesPath, "examples/rulesManagerBroken/shouldNotLoad.yaml")
    t.assertRegex(nrf.exception.message, r"ScannerError.*mapping values")
    t.assertRegex(
      repr(mock_logging.error.call_args_list),
      r"ScannerError.*mapping values"
    )

  @patch('cputils.rulesManager.logging')
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

    msgCollection = SettlingDict(timeOut=0.3)

    await natsListener(
      nc, messageCollector(msgCollection),
      'types.register'
    )

    rm = RulesManager('registerRules', nc)
    rm.loadRulesFrom('examples/rulesManager')
    await rm.registerTypes()
    await asyncio.sleep(1)
    await msgCollection.waitUntilSettled()
    t.assertEqual(len(msgCollection), 1)
    t.assertTrue('types.register' in msgCollection)
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
    msgs = msgCollection['types.register']
    t.assertEqual(len(msgs), len(registeredTypes))
    for aMsg in msgs :
      t.assertTrue('typeName' in aMsg)
      typeName = aMsg['typeName']
      t.assertTrue(typeName in registeredTypes)
      t.assertTrue('extensions' in aMsg)
      t.assertEqual(aMsg['extensions'], registeredTypes[typeName])
      t.assertTrue('chefName' in aMsg)
      t.assertEqual(aMsg['chefName'], 'registerRules')
