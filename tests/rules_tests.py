""" The **rules_tests** module collects various tests of the
**RuleManager**. """

import asyncio
import os
import shutil
import unittest
from unittest.mock import patch
import yaml

from cputils.natsClient import NatsClient
from cputils.rulesManager import RulesManager, NoRulesFile, NoRulesDirectory
from tests.testUtils import asyncTestOfProcess

cputilsTestDir    = '/tmp/cputils-tests-rulesManager'

class TestRulesManager(unittest.TestCase):
  """ Test the Rules Manager. """


  # Create a simple directory structure, cputilsTestDir, in /tmp which we
  # can use in our tests.
  #
  def setUpClass() :
    """ Setup the tests by creating a private directory in /tmp """

    os.makedirs(os.path.join(cputilsTestDir, 'test01'), exist_ok=True)
    os.system("tree "+ cputilsTestDir)
    with open(os.path.join(cputilsTestDir, 'test01', 'silly.txt'), 'w') as f :
      f.write("This is a test")

  # Remove the cputilsTestDir directories
  #
  def tearDownClass() :
    """ Tear down the private directory in /tmp """

    shutil.rmtree(cputilsTestDir)

  @patch('cputils.rulesManager.logging')
  def test_loadRulesWithNoDir(t, mock_logging) :
    """Test loading rules from a directory which does not exist"""

    rm = RulesManager()
    with t.assertRaises(NoRulesDirectory) as nrd :
      rm.loadRulesFrom("/this/directory/does/not/exist")
    t.assertEqual(nrd.exception.rulesPath, "/this/directory/does/not/exist")
    mock_logging.error.assert_called_with(
      'No rules directory found at [/this/directory/does/not/exist]'
    )

  @patch('cputils.rulesManager.logging')
  def test_loadRulesWithBrokenYaml(t, mock_logging) :
    """Test loading rules from a broken YAML file"""

    rm = RulesManager()
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

    rm = RulesManager()
    rm.loadRulesFrom('examples/rulesManager')
    t.assertNotEqual(rm, {})
    t.assertIn('types', rm.rulesData)
    t.assertIn('cCodeFile', rm.rulesData['types'])
    t.assertIn('extensions', rm.rulesData['types']['cCodeFile'])
    t.assertEqual(rm.rulesData['types']['cCodeFile']['extensions'][0], '*.c')
    #print("--------------------------------")
    #print(yaml.dump(rm))
    #print("--------------------------------")

  ##########################################################################
  # Registering Artefact Types

  @asyncTestOfProcess(None)
  async def test_registerRules(t) :
    """ Make sure that any new Artefact types are sent to the
    ArtefactManager via NATS. """

    tests = {
      "artefact.register.type.contextDocument" : {
        "name": 'contextDocument',
        "extensions": [ "*.tex" ]
      }
    }
    nc = NatsClient("natsTypesListener", 10)
    await nc.connectToServers(["nats://localhost:8888"])
    def aCallback(aSubject, theSubject, aNATSMessage) :
      try:
        t.assertEqual(aSubject, "artefact.register.type.*")
        if theSubject in tests :
          t.assertEqual(aNATSMessage, tests[theSubject], msg=theSubject)
          del tests[theSubject]
        if len(tests) == 0 :
          t.asyncTestDone(None)
      except Exception as err :
        t.asyncTestRaise(err)
    await nc.listenToSubject('artefact.register.type.*', aCallback)
    rm = RulesManager()
    rm.loadRulesFrom('examples/rulesManager')
    await rm.registerTypes(nc)
    for i in range(100) :
      if len(tests) == 0 :
        await nc.closeConnection()
        t.asyncTestDone(None)
        break
      await asyncio.sleep(0.01)
    t.assertEqual(len(tests), 0, msg="Not all tests found")

  ##########################################################################
  # Dealing with build.howTo requests


  async def natsBuildHowToListener(t) :
    pass

  @unittest.skip("No real tests yet")
  @asyncTestOfProcess(natsBuildHowToListener)
  async def test_ruleManagerBuildHowTo(t) :
    """ Test the **RuleManager** """

    t.assertTrue(True)
