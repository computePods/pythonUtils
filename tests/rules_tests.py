"""
The **rules_tests** module collects various tests of the **RuleManager**.
"""

import os
import shutil
import unittest

import cputils.rulesManager
from tests.testUtils import asyncTestOfProcess

cputilsTestDir    = '/tmp/cputils-tests-rulesManager'

class TestRulesManager(unittest.TestCase):
  """
  Test the Rules  Manager.
  """


  # Create a simple directory structure, cputilsTestDir, in /tmp which we
  # can use in our tests.
  #
  def setUpClass() :
    """
    Setup the tests by creating a private directory in /tmp
    """
    os.makedirs(os.path.join(cputilsTestDir, 'test01'), exist_ok=True)
    os.system("tree "+ cputilsTestDir)
    with open(os.path.join(cputilsTestDir, 'test01', 'silly.txt'), 'w') as f :
      f.write("This is a test")

  # Remove the cputilsTestDir directories
  #
  def tearDownClass() :
    """
    Tear down the private directory in /tmp
    """
    shutil.rmtree(cputilsTestDir)

  @unittest.skip("No real tests yet")
  def test_loadRules(t) :
    """

    When loading a rule set, we want to make sure that any new Artefact
    types are sent to the ArtefactManager via NATS.

    """
    cputils.rulesManager.loadRules('../examples/rulesManager')

  ##########################################################################
  # Registering Artefact Types



  ##########################################################################
  # Dealing with build.howTo requests

#  async def ruleManagerRunner(t) :
#    aWatcher = FSWatcher()
#    asyncio.create_task(aWatcher.managePathsToWatchQueue())
#    asyncio.create_task(aWatcher.manageComputeSHA256Queue())
#    print("\n")
#    await aWatcher.watchAPath(cputilsTestDir)
#    async for event in aWatcher.watch_recursive() :
#      logging.info(f'MAIN: got {event} for path {event.path}\n')
#      t.asyncTestQueue.put_nowait(event)

#  @unittest.skip("No real tests yet")

  @asyncTestOfProcess()
  async def test_ruleManager(t) :
    """
    Test the **RuleManager**
    """
    t.assertTrue(True)