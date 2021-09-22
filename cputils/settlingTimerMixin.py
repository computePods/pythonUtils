"""
A simple settlingTimerMixin.

This settling timer mixin class implements a collection of "debouncing
timers" which each clears after a configurable time (default: 0.01
seconds).

This mixin can also be configured to send a "settled" NATS message
(default: no message).

We implement this mixin by monkey patching a given class.

To add this mixin to a class you supply the class object to the
`mixinSettlingTimer`, you can then use the `addSettlingTimer` to add
additional timers.

Every object with a settling timer has a `main` timer, they may have one
or more other timers.

"""

import asyncio
import yaml

class SettlingTimer :
  def __init__(
    self,
    timerName,
    timeOut=0.01,
    aCallback=None,
  ) :
    if timeOut is None    : timeOut = 0.01

    self.timeOut     = timeOut
    self.callback    = aCallback
    self.hasSettled  = True
    self.future      = None

def mixinSettlingTimer(
  klass,
  mainTimeOut=0.01,
  mainCallback=None,
) :
  """Mixin the settling (debouncing) timer to the supplied class.

    - `timeOut` : the settling timer will sleep for timeOut seconds before
      determining that the instance's values have settled.

    - `aCallback` : an async python method which will be called when the
      timer settles (this can be used, for example, to send a NATS
      message which contains details of the settled object).

  """

  timers         = {}
  timers['main'] = SettlingTimer('main', mainTimeOut, mainCallback)

  async def runSettlingTimer(timerName = 'main') :
    """Runs the settling timer."""

    if timerName not in timers : return

    timer = timers[timerName]
    timer.hasSettled = False
    await asyncio.sleep(timer.timeOut)
    timer.hasSettled = True

    if timer.callback is not None :
      await timer.callback()

  def hasSettled(timerName = 'main') :
    """Returns True if the class is not currently waiting for its settle
    timer."""

    if timerName not in timers : return True

    return timers[timerName].hasSettled

  klass.hasSettled = hasSettled

  async def unSettle(timerName = 'main') :
    """(re)Starts the settling timer."""

    if timerName not in timers : return

    timer = timers[timerName]

    if timer.future :
      timer.future.cancel()
      if not timer.future.done() :
        await asyncio.wait([timer.future])
    timer.future = asyncio.ensure_future(runSettlingTimer(timerName))

  klass.unSettle  = unSettle

  async def waitUntilSettled(timerName='main', sleepTime=0.01, maxSleeps=100) :

    if timerName not in timers : return

    timer = timers[timerName]
    for i in range(maxSleeps) :
      await asyncio.sleep(sleepTime)
      if timer.hasSettled : break
    await asyncio.sleep(sleepTime)

  klass.waitUntilSettled = waitUntilSettled

  def addSettlingTimer(
    timerName,
    timeOut=0.01,
    aCallback=None
  ) :

    if timerName in timers : return

    timers[timerName] = SettlingTimer(timerName, timeOut, aCallback)

  klass.addSettlingTimer = addSettlingTimer

def moveKWarg(key, kwargs, options) :
  if key in kwargs :
    options[key] = kwargs[key]
    del kwargs[key]

class SettlingDict(dict) :
  def __init__(self, *args, **kwargs) :
    options = {}
    moveKWarg('timeOut', kwargs, options)
    moveKWarg('natsCllient', kwargs, options)
    moveKWarg('natsSubject', kwargs, options)
    moveKWarg('natsMessage', kwargs, options)
    super().__init__(*args, **kwargs)
    mixinSettlingTimer(self, **kwargs)
