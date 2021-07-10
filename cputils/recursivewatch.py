# -*- coding: utf-8 -*-
# Copyright © 2020 Taylor C. Richberger (under an MIT license)
# Modifications (C) 2021 Stephen Gaito (under an Apache-2.0 license)

# The original code (examples/recursivewatch.py) has been taken from the
# https://gitlab.com/Taywee/asyncinotify project, on 2021/July/08,
# commit # 25b4aaf155d780027c8b9d7f17f5e8b25508c7ee

# The original code (examples/recursivewatch.py) has been adapted for use
# in the inotify2nats project using the original code's MIT license.

import asyncio
from asyncinotify import Inotify, Event, Mask
from pathlib import Path
import sys

def get_directories_recursive(path) :
  '''
  Recursively list all directories under path, including path itself, if
  it's a directory.

  The path itself is always yielded before its children are iterated, so you
  can pre-process a path (by watching it with inotify) before you get the
  directory listing.

  Passing a non-directory won't raise an error or anything, it'll just yield
  nothing.
  '''

  if path.is_dir() :
    yield path
    for child in path.iterdir():
      yield from get_directories_recursive(child)
  elif path.is_file() :
    yield path

def buildMask(maskList) :
  theMask = 0
  for aMask in maskList :
    aMaskValue = Mask[aMask.upper()]
    theMask = theMask | aMaskValue
  return theMask

async def watch_recursive(watches):
  with Inotify() as inotify:
    for aWatch in watches :

      mask = buildMask(aWatch['masks'])
      print(f'Mask: {mask}')
      for aFile in aWatch['files'] :
        print(f'AFile: {Path(aFile)}')
        for directory in get_directories_recursive(Path(aFile)):
          print(f'INIT: watching {directory}')
          inotify.add_watch(directory, mask | Mask.MOVED_FROM | Mask.MOVED_TO | Mask.CREATE | Mask.DELETE_SELF | Mask.IGNORED)

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
    async for event in inotify:

      # Add subdirectories to watch if a new directory is added.  We do
      # this recursively here before processing events to make sure we
      # have complete coverage of existing and newly-created directories
      # by watching before recursing and adding, since we know
      # get_directories_recursive is depth-first and yields every
      # directory before iterating their children, we know we won't miss
      # anything.
      if Mask.CREATE in event.mask and event.path is not None and event.path.is_dir():
        for directory in get_directories_recursive(event.path):
          print(f'EVENT: watching {directory}')
          inotify.add_watch(directory, mask | Mask.MOVED_FROM | Mask.MOVED_TO | Mask.CREATE | Mask.DELETE_SELF | Mask.IGNORED)

      # If there is at least some overlap, assume the user wants this event.
      if event.mask & mask:
        yield event
      else:
        # Note that these events are needed for cleanup purposes.
        # We'll always get IGNORED events so the watch can be removed
        # from the inotify.  We don't need to do anything with the
        # events, but they do need to be generated for cleanup.
        # We don't need to pass IGNORED events up, because the end-user
        # doesn't have the inotify instance anyway, and IGNORED is just
        # used for management purposes.
        print(f'UNYIELDED EVENT: {event}')


async def watchForInotifyEvents(watches, natsClient):
  async for event in watch_recursive(watches):
    #print(f'MAIN: got {event} for path {event.path}')
    theMsg = {
      'mask': str(event.mask),
      'path': str(event.path)
    }
    print(f'MAIN: {theMsg}')
    await natsClient.sendMessage("silly", theMsg)
