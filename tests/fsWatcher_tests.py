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
import yaml

from asyncinotify import Mask
from cputils.fsWatcher import FSWatcher, get_directories_recursive, mask2text
from tests.testUtils import asyncTestOfProcess

logger = logging.getLogger()
#logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

cputilsTestDir    = '/tmp/cputils-tests-fsWatcher'

class TestFSWatcher(unittest.TestCase):

  def setUpClass() :
    """Create a simple directory structure, cputilsTestDir, in /tmp which
    we can use in our tests."""

    os.makedirs(os.path.join(cputilsTestDir, 'test01'), exist_ok=True)
    os.system("tree "+ cputilsTestDir)
    with open(os.path.join(cputilsTestDir, 'test01', 'silly.txt'), 'w') as f :
      f.write("This is a test")
    loggedMsgs = []

  def tearDownClass() :
    """Remove the cputilsTestDir directories"""

    shutil.rmtree(cputilsTestDir)

  def test_get_directories_recursive(t):
    """Ensure the `get_directories_recursive` method can walk the file
    system."""

    someFiles = []
    for aFile in get_directories_recursive(Path(cputilsTestDir)) :
      someFiles.append(aFile)

    t.assertEqual(str(someFiles.pop()), os.path.join(cputilsTestDir, 'test01', 'silly.txt'))
    t.assertEqual(str(someFiles.pop()), os.path.join(cputilsTestDir, 'test01'))
    t.assertEqual(str(someFiles.pop()), cputilsTestDir)
    t.assertEqual(someFiles, [])


  async def watchRecursiveProcessRunner(t) :
    """This is our long running process which expects to run forever. We
    run the watch_recursive generator while the associated test method
    uses aiofiles to alter the file system. The watch_recrusive generator
    should notice these changes."""

    aWatcher = FSWatcher()
    asyncio.create_task(aWatcher.managePathsToWatchQueue())
    #asyncio.create_task(aWatcher.manageComputeSHA256Queue())
    print("\n")
    await aWatcher.watchAPath(cputilsTestDir)
    async for anEvent in aWatcher.watch_recursive() :
      #logging.info("---------------------------------------------------------\n")
      #logging.info(f'MAIN: got {anEvent} for path {anEvent.path}')
      thePath = str(anEvent.path)
      #logging.info(f"got: [{thePath}]")
      if thePath not in t.eventsCollection :
        t.eventsCollection[thePath] = []
      maskInt = int(anEvent.mask)
      if maskInt not in mask2text : maskInt = 0
      t.eventsCollection[thePath].append(mask2text[maskInt])

  @asyncTestOfProcess(watchRecursiveProcessRunner)
  async def test_watchRecursive(t) :
    """Ensure the `watch_recursive` method generates all the expected file
    system change envents."""

    t.eventsCollection = {}

    # create the txt paths we will use..
    test1Dir       = os.path.join(cputilsTestDir, 'test01')
    test2Dir       = os.path.join(cputilsTestDir, 'test02')
    sillyTxtPath   = os.path.join(cputilsTestDir, 'test01', 'silly.txt')
    sillyTxt2Path  = os.path.join(cputilsTestDir, 'test01', 'silly.txt2')
    sillyTxt3Path  = os.path.join(cputilsTestDir, 'test01', 'silly.txt3')
    sillierTxtPath = os.path.join(cputilsTestDir, 'test01', 'sillier.txt')
    async with aiofiles.open(sillyTxtPath, 'a') as f :
      await f.write("\nThis is another line\n")
    #await asyncio.sleep(1)
    async with aiofiles.open(sillierTxtPath, 'w') as f :
      await f.write("\nThis is another line\n")
    #await asyncio.sleep(1)
    await aioshutil.move(sillyTxtPath, sillyTxt2Path)
    #await asyncio.sleep(1)
    await aiofiles.os.mkdir(test2Dir)
    #await asyncio.sleep(1)
    await aioshutil.copy(sillyTxt2Path, sillyTxt3Path)
    #await asyncio.sleep(1)
    await aiofiles.os.remove(sillyTxt3Path)
    #await asyncio.sleep(1)
    await aioshutil.rmtree(test1Dir, ignore_errors=True)
    await asyncio.sleep(0.5)
    #print(yaml.dump(t.eventsCollection))
    t.assertTrue(sillyTxtPath in t.eventsCollection)
    t.assertTrue('Modify' in t.eventsCollection[sillyTxtPath])
    t.assertTrue('CloseWrite' in t.eventsCollection[sillyTxtPath])
    t.assertTrue('MovedFrom' in t.eventsCollection[sillyTxtPath])
    t.assertTrue('Create' in t.eventsCollection[sillierTxtPath])
    t.assertTrue('Modify' in t.eventsCollection[sillierTxtPath])
    t.assertTrue('CloseWrite' in t.eventsCollection[sillierTxtPath])
    t.assertTrue('Delete' in t.eventsCollection[sillierTxtPath])
    t.assertTrue('MovedTo' in t.eventsCollection[sillyTxt2Path])
    t.assertTrue('Delete' in t.eventsCollection[sillyTxt2Path])
    t.assertTrue('Create' in t.eventsCollection[sillyTxt3Path])
    t.assertTrue('Modify' in t.eventsCollection[sillyTxt3Path])
    t.assertTrue('CloseWrite' in t.eventsCollection[sillyTxt3Path])
    t.assertTrue('Delete' in t.eventsCollection[sillyTxt3Path])
    t.assertTrue('DeletedDir' in t.eventsCollection[test1Dir])
    t.assertTrue('CreatedDir' in t.eventsCollection[test2Dir])