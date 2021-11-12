# -*- coding: utf-8 -*-
# Copyright © 2020 Taylor C. Richberger (under an MIT license)
# Modifications (C) 2021 Stephen Gaito (under an Apache-2.0 license)

# The original code (examples/recursivewatch.py) has been taken from the
# https://gitlab.com/Taywee/asyncinotify project, on 2021/July/08,
# commit # 25b4aaf155d780027c8b9d7f17f5e8b25508c7ee

# The original code (examples/recursivewatch.py) has been adapted for use
# in the ComputePods Utils project using the original code's MIT license.

import asyncio
from asyncinotify import Inotify, Event, Mask
import logging
from pathlib import Path
import sys
import traceback

NUM_SHA256_WORKERS = 3

# We want Mask.MASK_ADD so that watches are updated
# For the purposes of ComputePods we only care about:
# Mask.CREATE, Mask.MODIFY, Mask.MOVE, and Mask.DELETE
#
# Other potentially (remotely) relevant mask values might be:
# Mask.ACCESS would notify on any read/execs
# Mask.ATTRIB would notify on changes to timestamps, permissions, user/group ID
# Mask.CLOSE would notify on files being closed (after being opened?)
# Mask.OPEN would notify on files being opened
# Mask.UNMOUNT would notify on a file system being unmounted
#
cpMask = Mask.CLOSE_WRITE | Mask.CREATE | Mask.MODIFY | Mask.MOVE | Mask.DELETE
#
# Now we add in Masks we need for this module's book-keeping
#
wrMask = cpMask | Mask.MASK_ADD | Mask.MOVED_FROM | Mask.MOVED_TO | Mask.CREATE | Mask.DELETE_SELF | Mask.IGNORED

# A Mask to text mapping used to help test the fsWatcher
mask2text = {
  0 : 'Unknown',
  int(Mask.ACCESS) : 'Access',
  int(Mask.MODIFY) : 'Modify',
  int(Mask.CLOSE_WRITE) : 'CloseWrite',
  int(Mask.MOVED_FROM) : 'MovedFrom',
  int(Mask.MOVED_TO) : 'MovedTo',
  int(Mask.MOVE) : 'Move',
  int(Mask.CREATE) : 'Create',
  int(Mask.DELETE) : 'Delete',
  int(Mask.ISDIR) : 'IsDir',
  int(Mask.ISDIR | Mask.CREATE) : 'CreatedDir',
  int(Mask.ISDIR | Mask.DELETE) : 'DeletedDir',
}

def getMaskName(aMask) :
  """ Translate a raw Mask number into a human readable name. """

  maskName = ""
  for aPotentialMask, aPotentialName in mask2text.items() :
    if aMask & aPotentialMask :
      maskName = maskName + ' ' + aPotentialName
  return maskName.lstrip()

def get_directories_recursive(path) :
  """
  Recursively list all directories under path, including path itself, if
  it's a directory.

  The path itself is always yielded before its children are iterated, so you
  can pre-process a path (by watching it with inotify) before you get the
  directory listing.
  """

  if path.is_dir() :
    yield path
    for child in path.iterdir():
      yield from get_directories_recursive(child)
  elif path.is_file() :
    yield path

class FSWatcher :
  """ The file system watcher class (`FSWatcher`) uses the
  [asyncinotify](https://gitlab.com/Taywee/asyncinotify) project to
  monitor a Linux file system for changes. This code was originally based
  upon the asyncinotify project's `examples/recursivewatch.py` example."""

  def __init__(self, logger=None) :
    self.inotify               = Inotify()
    self.rootPaths             = []
    self.pathsToWatchQueue     = asyncio.Queue()
    self.computeSHA256Queue    = asyncio.Queue()
    self.fsWatchQueue          = asyncio.Queue()
    if logger is None : logger = logging.getLogger("FSWatcher")
    self.logger                = logger
    self.numWatches         = 0
    self.numUnWatches       = 0
    self.continueWatchingFS    = True

    # We want Mask.MASK_ADD so that watches are updated
    # For the purposes of ComputePods we only care about:
    # Mask.CREATE, Mask.MODIFY, Mask.MOVE, and Mask.DELETE
    #
    # Other potentially (remotely) relevant mask values might be:
    # Mask.ACCESS would notify on any read/execs
    # Mask.ATTRIB would notify on changes to timestamps, permissions, user/group ID
    # Mask.CLOSE would notify on files being closed (after being opened?)
    # Mask.OPEN would notify on files being opened
    # Mask.UNMOUNT would notify on a file system being unmounted
    #
    self.cpMask = cpMask
    #
    # Now we add in Masks we need for this module's book-keeping
    #
    self.wrMask = self.cpMask | Mask.MASK_ADD | Mask.MOVED_FROM | Mask.MOVED_TO | Mask.CREATE | Mask.DELETE_SELF | Mask.IGNORED

  def getRootPaths(self) :
    return self.rootPaths

  def stopWatchingFileSystem(self) :
    """(Gracefully) stop watching the file system"""

    self.continueWatchingFS = False

########################################################################

  def clearWatchStats(self) :
    self.numWatches   = 0
    self.numUnWatches = 0

  def getWatchStats(self) :
    return (self.numWatches, self.numUnWatches)

  async def watchAPath(self, pathToWatch) :
    """Add a file system path to the list of paths to be watched."""

    self.logger.debug("Adding path to watch queue {}".format(pathToWatch))
    await self.pathsToWatchQueue.put((True, pathToWatch, None))

  async def watchARootPath(self, pathToWatch) :
    """Add a single directory or file to the list of "root" paths to watch
    as well as schedule it to be watched. When one of the root paths is
    deleted, it will be re-watched."""

    self.logger.debug("Adding root path [{}]".format(pathToWatch))
    self.rootPaths.append(pathToWatch)
    await self.watchAPath(pathToWatch)

  async def unWatchAPath(self, pathToWatch, aWatch) :
    """ Add a single directory or file to be unWatched by this instance of
    `FSWatcher` to the `pathsToWatchQueue`. """

    self.logger.debug("Adding path to (un)watch queue {}".format(pathToWatch))
    await self.pathsToWatchQueue.put((False, pathToWatch, aWatch))

  async def managePathsToWatchQueue(self) :
    """A long running asyncio process which ensures all path in the list
    of paths are added to the inotify watch system.

    Implement all (pending) requests to watch/unWatch a directory or
    file which are in the `pathsToWatchQueue`.

    When watching, the paths contained in all directories are themselves
    recursively added to the `pathsToWatchQueue`. """

    while self.continueWatchingFS :
      addPath, aPathToWatch, theWatch = await self.pathsToWatchQueue.get()

      if addPath :
        for aPath in get_directories_recursive(Path(aPathToWatch)) :
          try :
            self.numWatches = self.numWatches + 1
            self.inotify.add_watch(aPath, wrMask)
            self.logger.info(f'INIT: watching {aPath}')
          except PermissionError as err :
            pass
          except Exception as err:
            print(f"Exception whild trying to watch: [{aPath}]")
            traceback.print_exc(err)
            # we can't watch this path just yet...
            # ... schedule its parent and try again...
            await self.watchAPath(aPath.parent)
      else :
        # according to the documentation.... the corresponding
        # Mask.IGNORE event will automatically remove this watch.
        #self.inotify.rm_watch(theWatch)
        self.numUnWatches = self.numUnWatches + 1
        self.logger.debug(f'INIT: unWatching {aPathToWatch}')
        if aPathToWatch in self.rootPaths :
          self.logger.debug(f'INIT: found root path... rewatching it {aPathToWatch}')
          await self.watchAPath(aPathToWatch)
      self.pathsToWatchQueue.task_done()

########################################################################

  async def computeSHA256For(self, aPath) :
    """Add a file to the list of file for which a SHA256 check sum will be
    computed."""

    print(f"Requesting computing SHA256 for [{aPath}]")
    await self.computeSHA256Queue.put(aPath)

  async def computeSHA256Worker(self, i) :
    """A long running asyncio process which ensures SHA256 checksums are
    computed for all files in the SHA256 file list."""

    print(f"Starting compute SHA256 worker {i}")
    while True :
      aPathToSHA256 = await self.computeSHA256Queue.get()
      self.logger.info(f"Computing SHA256 for [{aPathToSHA256}]")
      print(f"Computing SHA256 for [{aPathToSHA256}]")
      sha256Cmd = f"sha256sum {aPathToSHA256}"
      sha256Proc = await asyncio.create_subprocess_shell(
        sha256Cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

      stdout, stderr = await sha256Proc.communicate()

      print(f'[{sha256Cmd!r} exited with {sha256Proc.returncode}]')
      if stdout:
        print(f'[stdout]\n{stdout.decode()}')
      if stderr:
        print(f'[stderr]\n{stderr.decode()}')
      self.computeSHA256Queue.task_done()

  async def manageComputeSHA256Queue(self) :
    for i in range(1, NUM_SHA256_WORKERS + 1) :
      asyncio.create_task(self.computeSHA256Worker(i))

########################################################################

  #async def watch_recursive(self):
  async def watchForFileSystemEvents(self):
    """An asyncio/asyncinotify generator which generates file system
    change (Linux inotify) events for all watched files and
    directories."""

    # Things that can throw this off:
    #
    # * Moving a watched directory out of the watch tree (will still
    #   generate events even when outside of directory tree)
    #
    # * Doing two changes on a directory or something before the program
    #   has a time to handle it (this will also throw off a lot of inotify
    #   code, though)
    #
    # * Moving a watched directory within a watched directory will get the
    #   wrong path.  This needs to use the cookie system to link events
    #   together and complete the move properly, which can still make some
    #   events get the wrong path if you get file events during the move or
    #   something silly like that, since MOVED_FROM and MOVED_TO aren't
    #   guaranteed to be contiguous.  That exercise is left up to the
    #   reader.
    #
    # * Trying to watch a path that doesn't exist won't automatically
    #   create it or anything of the sort.
    #
    # * Deleting and recreating or moving the watched directory won't do
    #   anything special, but it probably should.
    #
    async for event in self.inotify:

      if not self.continueWatchingFS :
        return

      # If this is a creation event, add a watch for the new path (and its
      # subdirectories if any)
      #
      if Mask.CREATE in event.mask and event.path is not None :
        await self.watchAPath(event.path)

      if Mask.DELETE_SELF in event.mask and event.path is not None :
        await self.unWatchAPath(event.path, event.watch)

      # If there are some bits in the cpMask in the event.mask yield this
      # event
      #
      if event.mask & cpMask:
        #await self.computeSHA256For(event.path)
        yield event
      else:
        # Note that these events are needed for cleanup purposes.
        # We'll always get IGNORED events so the watch can be removed
        # from the inotify.  We don't need to do anything with the
        # events, but they do need to be generated for cleanup.
        # We don't need to pass IGNORED events up, because the end-user
        # doesn't have the inotify instance anyway, and IGNORED is just
        # used for management purposes.
        #
        self.logger.debug(f'UNYIELDED EVENT: {event}')

########################################################################

async def watchForInotifyEvents(watches, natsClient):
  """A long running asyncio process which forwards all file system change
  events to a NATS server."""

  async for event in watch_recursive(watches):
    # logger.info ( f'MAIN: got {event} for path {event.path}')
    theMsg = {
      'mask': str(event.mask),
      'path': str(event.path)
    }
    logger.info(f'MAIN: {theMsg}')
    await natsClient.sendMessage("silly", theMsg)
