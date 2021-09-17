"""
A simple settlingTimerMixin.

This settling timer mixin class implements a "debouncing timer" which clears
itself after a configurable time (default: 0.01 seconds).

This mixin can also be configured to send a "settled" NATS message
(default: no message).

We implement this mixin by monkey patching a given class.

To add this mixin to a class you supply the class object to the
`mixinSettlingTimer`.

"""

import asyncio

def mixinSettlingTimer(
  klass,
  timeOut=0.01,
  natsClient=None,
  natsSubject=None,
  natsMessage="settled"
) :
  """Mixin the settling (debouncing) timer to the supplied class.

    - `timeOut` : the settling timer will sleep for timeOut seconds before
      determining that the instance's values have settled.

    - `natsClient` : the NATS client used to send a 'settled' message.
      (Messages will only be sent if this parameter is not None)

    - `natsSubject` : the NATS subject over which to send a 'settled'
      message. (Messages will only be sent if this parameter is not None)

    - 'natsMessage' : the body of the NATS 'settled' message.

  """

  timerHasSettled     = True
  settlingTimerFuture = None

  async def runSettlingTimer() :
    """Runs the settling timer."""

    nonlocal timerHasSettled

    timerHasSettled = False
    await asyncio.sleep(timeOut)
    timerHasSettled = True

    if (natsClient and natsSubject) :
      await natsClient.sendMessage(natsSubject, natsMessage )

  def hasSettled() :
    """Returns True if the class is not currently waiting for its settle
    timer."""

    return timerHasSettled

  klass.hasSettled = hasSettled

  async def unSettle() :
    """(re)Starts the settling timer."""

    nonlocal settlingTimerFuture

    if settlingTimerFuture :
      settlingTimerFuture.cancel()
      if not settlingTimerFuture.done() :
        await asyncio.wait([settlingTimerFuture])
    settlingTimerFuture = asyncio.ensure_future(runSettlingTimer())

  klass.unSettle  = unSettle