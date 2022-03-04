""" This cputils.debouncingTaskRunner module implements the running of a
single task.

----

The following description is illustrated in the interaction diagram below.

The top level `runTasks` method initiates an `asyncio.Tasks` running the
`watchDo` method for each watch-do task. The `watchDo` method `reStart`s
an `asyncio.Task`, `taskRunner`, via a call to `asyncio.ensure_future`, to
manage a (potentially long running) OS process. The `watchDo` task
listens, in an `FSWatcher.watchForFileSystemEvents` loop, for any file
system changes which might be happening, `reStart`ing the `taskRunner`
task on any such changes.

The `taskRunner` task starts by sleeping, during which time the
`taskRunner` task can be cancelled and `reStart`ed (by a `watchDo`
task). This short timeout period of cancel-able sleep acts as a debouncing
timer. It allows a `watchDo` task to frequently `reStart` the
`taskRunner` task without actually running the external OS process until
any nearly simultaneous file system changes have stopped.

If the `taskRunner` is not cancelled during the sleep, the `taskRunner`
starts the OS process, using a call to `asyncio.create_subprocess_exec`,
and then creates two further `asyncio.Tasks`, `captureStdout` and
`captureRetCode`, to manage the process's output as well as to wait for
the process's return code.

Once an external OS process has been started, any `reStart` requests from
the `watchDo` task, signals the `captureStdout` task to stop listening for
the process's stdout, and then sends a `SIGHUP` signal to the process
(which *must* respond by gracefully exiting). The `watchDo` task then
`wait`s on the `taskRunner` task to finish before creating a new
`taskRunner` task (and potentially repeating this cycle).

----

In this interaction diagram, each `asyncio.Task` is represented by the
function which the task runs. The `OSproc` thread is an external OS
process, which is the ultimate "task" of a given watch-do task.

```mermaid

sequenceDiagram
  participant main
  participant runTasks
  participant watchDo
  participant taskRunner
  participant captureRetCode
  participant captureStdout
  participant OSproc

  activate main
  main-->>runTasks: run

  activate runTasks
  runTasks-->>watchDo: create_task

  activate watchDo
  Note over watchDo,OSproc: running (one watchDo for each watch-do task) ...
  watchDo-->>watchDo: reStart

  watchDo-->>watchDo: stopTaskProc
  Note over watchDo,OSproc: no task/proc running so stopTaskProc does nothing

  watchDo-->>taskRunner: ensure_future

  activate taskRunner
  taskRunner-->>taskRunner: sleep
  Note over taskRunner: a watchDo reStart<br/>at this point<br/>can cancel<br/>taskRunner<br/>while sleeping
  taskRunner-->>OSproc: exec
  activate OSproc
  taskRunner-->>captureStdout: wait on created task
  activate captureStdout
  taskRunner-->>captureRetCode: wait on created task
  activate captureRetCode

  OSproc-->>captureStdout: stdout
  OSproc-->>captureStdout: stdout
  OSproc-->>captureStdout: stdout

  Note over watchDo: file system<br/>change detected
  watchDo-->>watchDo: reStart
  watchDo-->>watchDo: stopTaskProc
  watchDo-->>OSproc: send SIGHUP
  OSproc-->>captureRetCode: finished
  deactivate OSproc
  captureRetCode-->>taskRunner: finished
  deactivate captureRetCode
  watchDo-->>captureStdout: continueCapturingStdout = False
  captureStdout-->>taskRunner: finished
  deactivate captureStdout
  watchDo-->>taskRunner: wait
  taskRunner-->>watchDo: done
  deactivate taskRunner

  watchDo-->>taskRunner: ensure_future
  activate taskRunner
  Note over taskRunner,OSproc:  new taskRunner starts ...
  taskRunner-->>watchDo: done
  deactivate taskRunner

  main-->>runTasks: shutdown

  runTasks-->>watchDo: stop listening for<br/>file system events

  runTasks-->>watchDo: stop debouncing timers
  watchDo-->>watchDo: stopTaskProc

  watchDo-->>runTasks: done
  deactivate watchDo

  runTasks-->>main: done
  deactivate runTasks

  deactivate main
```

----

"""

# Use psutil.pids() (returns list of pids) to check if the task's pid is
# still running.

import aiofiles
import asyncio
import os
import sys
import time
import traceback

class NatsLogger:
  def __init__(self, natsClient, subject, logLevel=0) :
    self.nc       = natsClient
    self.subject  = subject
    self.logLevel = logLevel

  async def open(self) :
    pass

  async def write(self, aMsg) :
    if isinstance(aMsg, str) :
      aMsg = aMsg.splitlines()
    await self.nc.sendMessage(self.subject, "\"  {}\"".format(
      "\n  ".join(aMsg)
    ))

  async def flush(self) :
    pass

  async def critical(self, aMsg) :
    if 0 < self.logLevel :
      await self.nc.sendMessage(self.subject, f"\"C:{aMsg}\"")

  async def error(self, aMsg) :
    if 1 < self.logLevel :
      await self.nc.sendMessage(self.subject, f"\"E:{aMsg}\"")

  async def warning(self, aMsg) :
    if 2 < self.logLevel :
      await self.nc.sendMessage(self.subject, f"\"W:{aMsg}\"")

  async def info(self, aMsg) :
    if 3 < self.logLevel :
      await self.nc.sendMessage(self.subject, f"\"I:{aMsg}\"")

  async def debug(self, aMsg) :
    if 4 < self.logLevel :
      await self.nc.sendMessage(self.subject, f"\"D:{aMsg}\"")

  async def trace(self, aMsg) :
    if 5 < self.logLevel :
      await self.nc.sendMessage(self.subject, f"\"T:{aMsg}\"")

class FileLogger:
  def __init__(self, filePath, logLevel=0) :
    self.logFile     = None
    self.logFilePath = filePath
    self.logLevel    = logLevel

  async def open(self) :
   if self.logFilePath == "stdout" :
     if 3 < self.logLevel :
       sys.stdout.write("\nI:Opening stdout as logger\n")
     def opener(path, flags) :
       #return sys.stdout
       return os.dup(1)
     self.logFile = await aiofiles.open(
       "/dev/null", "w", opener=opener
     )
     return
   self.logFile = await aiofiles.open(
      os.path.abspath(os.path.expanduser(self.logFilePath)), "w"
    )

  async def write(self, aMsg) :
    if self.logFile is not None :
      if isinstance(aMsg, str) :
        aMsg = aMsg.splitlines(keepends=True)
      aMsg = "  ".join(aMsg)
      #print("["+aMsg+"]\n")
      await self.logFile.write(f"  {aMsg}")

  async def flush(self) :
    if self.logFile is not None :
      await self.logFile.flush()

  async def critical(self, aMsg) :
    if self.logFile is not None and 0 < self.logLevel :
      await self.logFile.write(f"C:{aMsg}\n")

  async def error(self, aMsg) :
    if self.logFile is not None and 1 < self.logLevel :
      await self.logFile.write(f"E:{aMsg}\n")

  async def warning(self, aMsg) :
    if self.logFile is not None and 2 < self.logLevel :
      await self.logFile.write(f"W:{aMsg}\n")

  async def info(self, aMsg) :
    if self.logFile is not None and 3 < self.logLevel :
      await self.logFile.write(f"I:{aMsg}\n")

  async def debug(self, aMsg) :
    if self.logFile is not None and 4 < self.logLevel :
      await self.logFile.write(f"D:{aMsg}\n")

  async def trace(self, aMsg) :
    if self.logFile is not None and 5 < self.logLevel :
      await self.logFile.write(f"T:{aMsg}\n")

class RegExpLogger:
  def __init__(self, collection, regExps, logLevel=0) :
    self.collection = collection
    compiledRegExps = []
    for aTag, aRegExp in regExps.items() :
      compiledRegExps[aTag] = re.compile(aRegExp)
    self.regExps    = compiledRegExps

  async def open(self) :
    pass

  def captureRegExps(self, aMsg, logTag) :
    captures = {}
    for aTag, aRegExp in self.regExps.items() :
      captures[aTag] = aRegExp.match(aMsg)
    if captures :
      self.collection.append((logTag, captures))

  async def write(self, aMsg) :
    self.captureRegExps(aMsg, "")

  async def flush(self) :
    pass

  async def critical(self, aMsg) :
    self.captureRegExps(aMsg, "critical")

  async def error(self, aMsg) :
    self.captureRegExps(aMsg, "error")

  async def warning(self, aMsg) :
    self.captureRegExps(aMsg, "warning")

  async def info(self, aMsg) :
    self.captureRegExps(aMsg, "info")

  async def debug(self, aMsg) :
    self.captureRegExps(aMsg, "debug")

  async def trace(self, aMsg) :
    self.captureRegExps(aMsg, "trace")

class MultiLogger:
  def __init__(self, arrayOfLoggers) :
    self.loggers = arrayOfLoggers

  async def open(self) :
    for aLogger in self.loggers :
      await aLogger.open()

  async def write(self, aMsg) :
    for aLogger in self.loggers :
      await aLogger.write(aMsg)

  async def flush(self) :
    for aLogger in self.loggers :
      await aLogger.flush()

  async def critical(self, aMsg) :
    for aLogger in self.loggers :
      await aLogger.critical(aMsg)

  async def error(self, aMsg) :
    for aLogger in self.loggers :
      await aLogger.error(aMsg)

  async def warning(self, aMsg) :
    for aLogger in self.loggers :
      await aLogger.warning(aMsg)

  async def info(self, aMsg) :
    for aLogger in self.loggers :
      await aLogger.info(aMsg)

  async def debug(self, aMsg) :
    for aLogger in self.loggers :
      await aLogger.debug(aMsg)

  async def trace(self, aMsg) :
    for aLogger in self.loggers :
      await aLogger.trace(aMsg)

class DebouncingTaskRunner:
  """ The DebouncingTaskRunner class implements a simple timer to ensure
  multiple (re)start events result in only one invocation of the task
  command. """

  def __init__(
    self, timeout,
    taskName, taskDetails, taskLog,
    terminateSignal,
    env=None,
    doneCallback=None
  ) :
    """ Create the debouncing task runner with a specific timeout and task
    definition.

    The taskDetails provides the command to run, the logging object used
    to record command output, as well as the project directory in which to
    run the command.

    The taskLog (logging object) MUST provide `write` and `flush` methods.
    The `write` method MUST take one string argument. """

    self.timeout    = timeout
    self.taskName   = taskName
    self.taskCmd    = taskDetails['cmd']
    self.taskCmdStr = " ".join(taskDetails['cmd'])
    self.taskLog    = taskLog
    self.taskDir    = taskDetails['projectDir']
    self.termSignal = terminateSignal
    self.taskFuture = None
    self.proc       = None
    self.pid        = None
    self.retCode    = None

    self.env        = None
    taskEnv = taskDetails['env']
    self.taskEnv    = taskEnv
    if taskEnv is not None and isinstance(taskEnv, dict) :
      localEnv = dict(os.environ)
      for aKey, aValue in taskEnv.items() :
        localEnv[aKey] = aValue
      self.env = localEnv

    if not callable(doneCallback) \
      or asyncio.iscoroutine(doneCallback) \
      or asyncio.iscoroutinefunction(doneCallback) :
      doneCallback = None
    self.doneCallback = doneCallback

    self.continueCapturingStdout = True

  async def cancelTimer(self) :
    """Cancel the Debouncing timer"""

    if self.taskFuture and not self.procIsRunning() :
      await self.taskLog.debug("Cancelling timer for {}".format(self.taskName))
      self.taskFuture.cancel()

  def procIsRunning(self) :
    """Determine if an external process is (still) running"""

    return self.proc is not None and self.proc.returncode is None

  def getReturnCode(self) :
    """Return the underlying processes return code.
    Returns None if the process is still running."""

    return self.retCode

  async def stopTaskProc(self) :
    """Stop the external process"""

    taskLog = self.taskLog
    await taskLog.debug("Attempting to stop the task process for {}".format(self.taskName))
    self.continueCapturingStdout = False
    if self.proc is not None :
      pid = self.proc.pid
      await taskLog.debug("Process found for {} ({})".format(self.taskName, pid))
      if self.procIsRunning() :
        await taskLog.debug("Process still running for {}".format(self.taskName))
        try:
          await taskLog.debug("Sending OS signal ({}) to {} (pid:{})".format(
            self.termSignal, self.taskName, pid
          ))
          self.proc.send_signal(self.termSignal)
        except ProcessLookupError :
          await taskLog.debug("No exiting external process found for {} (pid:{})".format(
            self.taskName, pid
          ))
        except Exception as err:
          await taskLog.error("Could not send signal ({}) to proc for {} (})".format(
            self.termSignal, self.taskName, pid
          ))
          await taskLog.error(repr(err))
          traceback.print_exc()
      else :
        self.retCode = self.proc.returncode
        await taskLog.debug("Process finished with return code {} for {}".format(
          self.retCode, self.taskName
        ))
    else :
      await taskLog.debug("No external process found for {}".format(self.taskName))

  async def captureOutput(self) :
    """Capture the (stdout) output from the external process"""

    taskLog = self.taskLog
    await taskLog.debug("CaptureOutput task running for {}".format(self.taskName))
    if self.proc is not None :
      stdout = self.proc.stdout
      if stdout :

        await taskLog.write("\n============================================================================\n")
        await taskLog.write("{} ({}) stdout @ {}\n".format(
          self.taskName, self.proc.pid, time.strftime("%Y/%m/%d %H:%M:%S")
        ))
        await taskLog.write("{}\n".format(self.taskCmdStr))
        await taskLog.write("----------------------------------------------------------------------------\n")
        await taskLog.flush()
        while self.continueCapturingStdout and not stdout.at_eof() :
          await taskLog.trace("Collecting {} stdout ({})".format(
            self.taskName, self.proc.pid
          ))
          aLine = await stdout.readline()
          await taskLog.write(aLine.decode())
          await taskLog.flush()
        if self.continueCapturingStdout :
          await taskLog.debug("Finshed collecting {} stdout ({})".format(
            self.taskName, self.proc.pid
          ))
        else :
          await taskLog.write("\n[Stopped collecting stdout]")
          await taskLog.debug("Stopped collecting process stdout for {} ({})".format(
            self.taskName, self.pid
          ))
        await taskLog.write("\n----------------------------------------------------------------------------\n")
        await taskLog.write("{} ({}) stdout @ {}\n".format(
          self.taskName, self.pid, time.strftime("%Y/%m/%d %H:%M:%S")
        ))
        await taskLog.flush()
      else :
        await taskLog.debug("No stdout found for {}".format(self.taskName))
    else :
      await taskLog.debug("No external process found so no stdout captured for {}".format(self.taskName))
    await taskLog.debug("CaptureOutput task finished for {}".format(self.taskName))

  async def captureRetCode(self) :
    """Wait for and capture the return code of the external process"""

    taskLog = self.taskLog
    await taskLog.debug("Capturing return code for {}".format(self.taskName))
    try :
      self.retCode = await self.proc.wait()
    except ProcessLookupError :
      await taskLog.debug("No process found for {} (pid:{})".format(
        self.taskName, self.pid
      ))
    if self.retCode is not None :
      retCode = self.retCode
      pid = self.pid
      await taskLog.debug("Return code for {} is {} (pid:{})".format(
        self.taskName, retCode, pid
      ))
      await taskLog.write("{} task ({}) exited with {}\n".format(
        self.taskName, pid, retCode
      ))
      await taskLog.write("\n")
      await taskLog.flush()
      await taskLog.debug("Finished {} ({}) command [{}] exited with {}".format(
        self.taskName, pid, self.taskCmdStr, retCode
      ))
    self.proc = None
    await taskLog.debug("Captured return code for {}".format(self.taskName))

  async def taskRunner(self) :
    """ Run the task's command, after sleeping for the timeout period,
    using `asyncio.create_subprocess_exec` command. """

    taskLog = self.taskLog

    try:
      await taskLog.debug("TaskRunner for {} sleeping for {}".format(
        self.taskName, self.timeout
      ))
      await asyncio.sleep(self.timeout)

      # Now we can run the new task...
      #
      await taskLog.debug("Running {} command [{}]".format(
        self.taskName, self.taskCmdStr
      ))
      self.proc = await asyncio.create_subprocess_exec(
        *self.taskCmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=self.taskDir,
        env=self.env
      )
      self.pid = self.proc.pid
      self.retCode = None
      self.continueCapturingStdout = True
      print(f'Ran: {self.taskName}')
      await  self.captureOutput(),
      await  self.captureRetCode()
      if self.continueCapturingStdout and (self.retCode is None or self.retCode != 0) :
        print(f"FAILED: {self.taskName} ({self.retCode})")
    except Exception as err :
      print("Caught exception while running {} task".format(self.taskName))
      print(repr(err))
      traceback.print_exc()

  async def reStart(self) :
    """ (Re)Start the timer. If the timer is already started, it is
    restarted with a new timeout period. """

    taskLog = self.taskLog

    await self.stopTaskProc()

    if self.taskFuture :
      await self.cancelTimer()
      if not self.taskFuture.done() :
        await taskLog.debug("Waiting for the previous taskRunner task for {} to finish".format(self.taskName))
        await asyncio.wait([self.taskFuture])

    await taskLog.debug("Starting new taskRunner for {}".format(self.taskName))
    self.taskFuture = asyncio.ensure_future(self.taskRunner())
    if self.doneCallback :
      def wrappedDoneCallback(aFuture) :
        self.doneCallback()
      self.taskFuture.add_done_callback(wrappedDoneCallback)
