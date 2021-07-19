import os
import shutil
import unittest

import cputils.rulesManager
from tests.testUtils import asyncTestOfProcess

cputilsTestDir    = '/tmp/cputils-tests-rulesManager'

class TestRulesManager(unittest.TestCase):

  # Create a simple directory structure, cputilsTestDir, in /tmp which we
  # can use in our tests.
  #
  def setUpClass() :
    os.makedirs(os.path.join(cputilsTestDir, 'test01'), exist_ok=True)
    os.system("tree "+ cputilsTestDir)
    with open(os.path.join(cputilsTestDir, 'test01', 'silly.txt'), 'w') as f :
      f.write("This is a test")

  # Remove the cputilsTestDir directories
  #
  def tearDownClass() :
    shutil.rmtree(cputilsTestDir)

  @unittest.skip("No real tests yet")
  def test_loadRules(t) :
    cputils.rulesManager.loadRules('../examples/rulesManager')

  ##########################################################################
  # Registering Artefact Types



  ##########################################################################
  # Dealing with build.howTo requests

  async def ruleManagerRunner(t) :
    aWatcher = FSWatcher()
    asyncio.create_task(aWatcher.managePathsToWatchQueue())
    asyncio.create_task(aWatcher.manageComputeSHA256Queue())
    print("\n")
    await aWatcher.watchAPath(cputilsTestDir)
    async for event in aWatcher.watch_recursive() :
      logging.info(f'MAIN: got {event} for path {event.path}\n')
      t.asyncTestQueue.put_nowait(event)

  @unittest.skip("No real tests yet")
  @asyncTestOfProcess(ruleManagerRunner)
  async def test_watchRecursive(t) :
    async with aiofiles.open(os.path.join(cputilsTestDir, 'test01', 'silly.txt'), 'a') as f :
      await f.write("\nThis is another line\n")
    await asyncio.sleep(10)
    async with aiofiles.open(os.path.join(cputilsTestDir, 'test01', 'sillier.txt'), 'w') as f :
      await f.write("\nThis is another line\n")
    await asyncio.sleep(10)
    await aioshutil.move(
      os.path.join(cputilsTestDir, 'test01', 'silly.txt'),
      os.path.join(cputilsTestDir, 'test01', 'silly.txt2')
    )
