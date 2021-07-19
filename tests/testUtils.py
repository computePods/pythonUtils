import asyncio

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

# The asyncTestOfProcess decorator expects as an *argument* an async
# coroutine which runs the long running asynchronous process to be
# tested. The asyncTestOfProcess *decorates* another async coroutine
# containing the tests and assertions used to test the long running
# process itself. Both the argument and the decorated function MUST be
# async coroutines, AND the process needs to place "things" into the
# t.asyncTestQueue, AND the decorated function MUST await on
# t.asyncTestQueue.get() to allow the tested process time to function.

def asyncTestOfProcess(asyncProcessFunc) :
  def decorateTest(asyncTestFunc) :
    def wrappedTest(t) :
      async def asyncRunner() :
        t.asyncTestQueue = asyncio.Queue()
        if not asyncio.iscoroutinefunction(asyncProcessFunc) :
          t.fail("The process being tested MUST be a async coroutine!")
        if not asyncio.iscoroutinefunction(asyncTestFunc) :
          t.fail("The test being run on the process MUST be a async coroutine!")
        processRunner = asyncio.create_task(asyncProcessFunc(t))
        asyncTestFuture = asyncio.get_event_loop().create_future()
        async def wrappedAsyncTestFunc() :
          try :
            await asyncTestFunc(t)
            asyncTestFuture.set_result(None)
          except asyncio.CancelledError :
            pass
          except Exception as err :
            asyncTestFuture.set_exception(err)
        testRunner = asyncio.create_task(wrappedAsyncTestFunc())
        await asyncTestFuture
      try :
        asyncio.run(asyncRunner())
      except asyncio.CancelledError :
        pass
    return wrappedTest
  return decorateTest

