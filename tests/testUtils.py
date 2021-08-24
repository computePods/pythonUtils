import asyncio
import functools

# These asyncio tests have been inspired by Miguel Grinberg's excellent
# article:
#    https://blog.miguelgrinberg.com/post/unit-testing-asyncio-code

# We really want a decorator on a PAIR of functions...
# https://stackoverflow.com/questions/46018980/python-decorator-for-multiple-functions-as-arguments
#
# But instead we use the "Decorator with arguments" pattern from:
#   https://realpython.com/primer-on-python-decorators/
# (Which is essentially the answer in the above Stack Overflow question)

# The use of the "t.asyncTestFuture" has been suggested by:
#   https://stackoverflow.com/a/53691009

# A good look at exception handling in tasks...
#  https://quantlane.com/blog/ensure-asyncio-task-exceptions-get-logged/

def asyncTestOfProcess(asyncProcessFunc=None) :
  """ The asyncTestOfProcess **decorator** expects as an *argument* an
  async coroutine which runs a long running asynchronous *process* to be
  tested.

  The asyncTestOfProcess *decorates* another async coroutine containing
  the *tests and assertions* used to test the long running process itself.

  Both the argument (if it exists) and the decorated
  function MUST be async coroutines.

  The process can place "things" into the t.asyncTestQueue, which the
  tests in the decorated function can await on t.asyncTestQueue.get() to
  allow the process time to function.

  Exceptions in either the process or decorated function tests SHOULD be
  set on the t.asyncTestFuture using the `set_exception` function. This
  will ensure the exception gets propagated to the unit test itself.

  Tests SHOULD set the t.asyncTestFuture result when they are complete.
  """

  def decorateTest(asyncTestFunc) :
    @functools.wraps(asyncTestFunc)
    def wrappedTest(t) :
      async def asyncRunner() :
        t.asyncTestQueue = asyncio.Queue()
        t.asyncTestFuture = asyncio.get_event_loop().create_future()

        def asyncTestDone(aResult) :
          if not t.asyncTestFuture.done() :
            t.asyncTestFuture.set_result(aResult)
        t.asyncTestDone = asyncTestDone

        def asyncTestRaise(anException) :
          if not t.asyncTestFuture.done() :
            t.asyncTestFuture.set_exception(anException)
        t.asyncTestRaise = asyncTestRaise


        if asyncProcessFunc :
          if not asyncio.iscoroutinefunction(asyncProcessFunc) :
            t.fail("The process being tested MUST be a async coroutine!")
          asyncio.create_task(asyncProcessFunc(t))

        if not asyncio.iscoroutinefunction(asyncTestFunc) :
          t.fail("The test being run on the process MUST be a async coroutine!")
        async def wrappedAsyncTestFunc() :
          try :
            await asyncTestFunc(t)
            t.asyncTestFuture.set_result(None)
          except asyncio.CancelledError :
            pass
          except Exception as err :
            t.asyncTestFuture.set_exception(err)
        asyncio.create_task(wrappedAsyncTestFunc())
        await t.asyncTestFuture
        t.asyncTestFuture.result()

      try :
        asyncio.run(asyncRunner())
      except asyncio.CancelledError :
        pass

    return wrappedTest

  return decorateTest

