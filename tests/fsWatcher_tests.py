import aiofiles
import aiofiles.os
import aioshutil
import asyncio
import logging
import os
from pathlib import Path
import shutil
import time
import unittest
from unittest import mock

from asyncinotify import Mask
from cputils.fsWatcher import FSWatcher, get_directories_recursive
from tests.testUtils import asyncTestOfProcess

logger = logging.getLogger()
#logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

cputilsTestDir    = '/tmp/cputils-tests-fsWatcher'

class TestRecursiveWatch(unittest.TestCase):

  # Create a simple directory structure, cputilsTestDir, in /tmp which we
  # can use in our tests.
  #
  def setUpClass() :
    os.makedirs(os.path.join(cputilsTestDir, 'test01'), exist_ok=True)
    os.system("tree "+ cputilsTestDir)
    with open(os.path.join(cputilsTestDir, 'test01', 'silly.txt'), 'w') as f :
      f.write("This is a test")
    loggedMsgs = []

  # Remove the cputilsTestDir directories
  #
  def tearDownClass() :
    shutil.rmtree(cputilsTestDir)

  def test_get_directories_recursive(t):
    someFiles = []
    for aFile in get_directories_recursive(Path(cputilsTestDir)) :
      someFiles.append(aFile)

    t.assertEqual(str(someFiles.pop()), os.path.join(cputilsTestDir, 'test01', 'silly.txt'))
    t.assertEqual(str(someFiles.pop()), os.path.join(cputilsTestDir, 'test01'))
    t.assertEqual(str(someFiles.pop()), cputilsTestDir)
    t.assertEqual(someFiles, [])

  # This is our long running process which expects to run forever. We run
  # the watch_recursive generator while the test method uses aiofiles to
  # alter the file system. The watch_recrusive generator should notice
  # these changes.

  async def watchRecursiveProcessRunner(t) :
    aWatcher = FSWatcher()
    asyncio.create_task(aWatcher.managePathsToWatchQueue())
    asyncio.create_task(aWatcher.manageComputeSHA256Queue())
    print("\n")
    await aWatcher.watchAPath(cputilsTestDir)
    async for event in aWatcher.watch_recursive() :
      logging.info(f'MAIN: got {event} for path {event.path}\n')
      t.asyncTestQueue.put_nowait(event)

  # This is the actual unit test which will use aiofiles to alter the file
  # system. We expect to see these changes logged by the python logger.

  async def collectEvents(t) :
    events = {}
    #await asyncio.sleep(1)
    while not t.asyncTestQueue.empty() :
      anEvent = await t.asyncTestQueue.get()
      thePath = str(anEvent.path)
      print(f"\ngot: [{thePath}]")
      if thePath in events :
        events[thePath] = events[thePath] | anEvent.mask
      else :
        events[thePath] = anEvent.mask
      t.asyncTestQueue.task_done()
    return events

  @unittest.skip("No real tests yet")
  @asyncTestOfProcess(watchRecursiveProcessRunner)
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
    await asyncio.sleep(10)
    await aiofiles.os.mkdir(
      os.path.join(cputilsTestDir, 'test02')
    )
    await asyncio.sleep(10)
    await aioshutil.copy(
      os.path.join(cputilsTestDir, 'test01', 'silly.txt2'),
      os.path.join(cputilsTestDir, 'test01', 'silly.txt3')
    )
    await asyncio.sleep(10)
    await aiofiles.os.remove(
      os.path.join(cputilsTestDir, 'test01', 'silly.txt3')
    )
    await asyncio.sleep(10)
    await aioshutil.rmtree(
      os.path.join(cputilsTestDir, 'test01'),
      ignore_errors=True
    )
    print("\nawaiting asyncTestQueue\n")
    await asyncio.sleep(150)
    #theEvents = await t.collectEvents()
    #print(theEvents)
    #t.assertEqual(str(theEvent.path), '/tmp/cputils-tests/test01/silly.txt')
    #t.assertEqual(t.asyncTestQueue.qsize(), 0)
