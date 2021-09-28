import asyncio
import unittest
import yaml

from cputils.natsClient import NatsClient

from cputils.artefactManager import ArtefactManager
from cputils.tasksManager    import TasksManager

from cputils.settlingTimerMixin import SettlingDict
from cputils.natsListener import ( natsListener, messageCollector,
   hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestArtefactsManager(unittest.TestCase) :
  """Test the ArtefactsManager"""

  @asyncTestOfProcess(None)
  async def test_listenForTasks(t) :
    """Test the ArtefactManager's ability to listen for task messages."""

    nc = NatsClient("taskListener", 10)
    await nc.connectToServers(["nats://localhost:8888"])

    am = ArtefactManager(nc)
    await am.listenForTaskMessages()

    artefactsCollection = SettlingDict(timeOut=0.3)
    await natsListener(
      nc, messageCollector(artefactsCollection),
      'registered.artefacts'
    )
    tasksCollection = SettlingDict(timeOut=0.3)
    await natsListener(
      nc, messageCollector(tasksCollection),
      'registered.tasks'
    )

    tm = TasksManager('listenForTasks', nc)
    tm.loadTasksFrom('examples/projectManager/joylol')
    await tm.registerTasks()
    await asyncio.sleep(1)
    await am.waitUntilSettled('taskRegistration')

    testTasks = {
      "joylol-memory": {
        "chefName": "registerTasks",
        "taskName": "joylol-memory",
        "theTask": {
          "rule": "joylol",
          "dependencies": [
            "memory/memory.joy"
          ],
          "outputs": [
            "memory/memory.jout"
          ]
        }
      },
      "joylol-parser": {
        "chefName": "registerTasks",
        "taskName": "joylol-parser",
        "theTask": {
          "rule": "joylol",
          "dependencies": [
            "parser/parser.joy"
          ],
          "outputs": [
            "parser/parser.jout"
          ]
        }
      },
      "joylol-strings": {
        "chefName": "registerTasks",
        "taskName": "joylol-strings",
        "theTask": {
          "rule": "joylol",
          "dependencies": [
            "base/strings.joy"
          ],
          "outputs": [
            "base/strings.jout"
          ]
        }
      },
      "joylol-contexts": {
        "chefName": "registerTasks",
        "taskName": "joylol-contexts",
        "theTask": {
          "rule": "joylol",
          "dependencies": [
            "base/contexts.joy"
          ],
          "outputs": [
            "base/contexts.jout"
          ]
        }
      },
      "joylol-cFunctions": {
        "chefName": "registerTasks",
        "taskName": "joylol-cFunctions",
        "theTask": {
          "rule": "joylol",
          "dependencies": [
            "base/cFunctions.joy"
          ],
          "outputs": [
            "base/cFunctions.jout"
          ]
        }
      },
      "joylol-luaFunctions": {
        "chefName": "registerTasks",
        "taskName": "joylol-luaFunctions",
        "theTask": {
          "rule": "joylol",
          "dependencies": [
            "base/luaFunctions.joy"
          ],
          "outputs": [
            "base/luaFunctions.jout"
          ]
        }
      },
      "joylol-joylolFunctions": {
        "chefName": "registerTasks",
        "taskName": "joylol-joylolFunctions",
        "theTask": {
          "rule": "joylol",
          "dependencies": [
            "base/joylolFunctions.joy"
          ],
          "outputs": [
            "base/joylolFunctions.jout"
          ]
        }
      },
      "joylol-interpreter": {
        "chefName": "registerTasks",
        "taskName": "joylol-interpreter",
        "theTask": {
          "rule": "joylol",
          "dependencies": [
            "interpreter/interpreter.joy"
          ],
          "outputs": [
            "interpreter/interpreter.jout"
          ]
        }
      },
      "context": {
        "chefName": "registerTasks",
        "taskName": "context",
        "theTask": {
          "rule": "context",
          "dependencies": [
            "joylol.tex",
            "memory/memory.tex",
            "parser/parser.tex",
            "base/strings.tex",
            "base/contexts.tex",
            "base/functions.tex",
            "interpreter/interpreter.tex"
          ],
          "secondaryDependencies": [
            "joylol.lua",
            "memory/memory.jout",
            "parser/parser.jout",
            "base/strings.jout",
            "base/contexts.jout",
            "base/cFunctions.jout",
            "base/luaFunctions.jout",
            "base/joylolFunctions.jout",
            "interpreter/interpreter.jout"
          ],
          "outputs": [
            "joylol.pdf",
            "joylol.lua",
            "memory/memory.c",
            "memory/memory.h",
            "memory/memory.joy",
            "parser/parser.c",
            "parser/parser.h",
            "parser/parser.joy",
            "base/strings.c",
            "base/strings.h",
            "base/strings.joy",
            "base/contexts.c",
            "base/contexts.h",
            "base/contexts.joy",
            "base/cFunctions.c",
            "base/cFunctions.h",
            "base/cFunctions.joy",
            "base/luaFunctions.c",
            "base/luaFunctions.h",
            "base/luaFunctions.joy",
            "base/joylolFunctions.c",
            "base/joylolFunctions.h",
            "base/joylolFunctions.joy",
            "interpreter/interpreter.c",
            "interpreter/interpreter.h",
            "interpreter/interpreter.joy"
          ]
        }
      },
      "cc-memory": {
        "chefName": "registerTasks",
        "taskName": "cc-memory",
        "theTask": {
          "rule": "objectFiles",
          "dependencies": [
            "memory/memory.c",
            "memory/memory.h"
          ],
          "outputs": [
            "memory/memory.o"
          ]
        }
      },
      "cc-parser": {
        "chefName": "registerTasks",
        "taskName": "cc-parser",
        "theTask": {
          "rule": "objectFiles",
          "dependencies": [
            "parser/parser.c",
            "parser/parser.h"
          ],
          "outputs": [
            "parser/parser.o"
          ]
        }
      },
      "cc-strings": {
        "chefName": "registerTasks",
        "taskName": "cc-strings",
        "theTask": {
          "rule": "objectFiles",
          "dependencies": [
            "base/strings.c",
            "base/strings.h"
          ],
          "outputs": [
            "base/strings.o"
          ]
        }
      },
      "cc-contexts": {
        "chefName": "registerTasks",
        "taskName": "cc-contexts",
        "theTask": {
          "rule": "objectFiles",
          "dependencies": [
            "base/contexts.c",
            "base/contexts.h"
          ],
          "outputs": [
            "base/contexts.o"
          ]
        }
      },
      "cc-cFunctions": {
        "chefName": "registerTasks",
        "taskName": "cc-cFunctions",
        "theTask": {
          "rule": "objectFiles",
          "dependencies": [
            "base/cFunctions.c",
            "base/cFunctions.h"
          ],
          "outputs": [
            "base/cFunctions.o"
          ]
        }
      },
      "cc-luaFunctions": {
        "chefName": "registerTasks",
        "taskName": "cc-luaFunctions",
        "theTask": {
          "rule": "objectFiles",
          "dependencies": [
            "base/luaFunctions.c",
            "base/luaFunctions.h"
          ],
          "outputs": [
            "base/luaFunctions.o"
          ]
        }
      },
      "cc-joylolFunctions": {
        "chefName": "registerTasks",
        "taskName": "cc-joylolFunctions",
        "theTask": {
          "rule": "objectFiles",
          "dependencies": [
            "base/joylolFunctions.c",
            "base/joylolFunctions.h"
          ],
          "outputs": [
            "base/joylolFunctions.o"
          ]
        }
      },
      "cc-interpreter": {
        "chefName": "registerTasks",
        "taskName": "cc-interpreter",
        "theTask": {
          "rule": "objectFiles",
          "dependencies": [
            "interpreter/interpreter.c",
            "interpreter/interpreter.h"
          ],
          "outputs": [
            "interpreter/interpreter.o"
          ]
        }
      },
      "link-joylol": {
        "chefName": "registerTasks",
        "taskName": "link-joylol",
        "theTask": {
          "rule": "applications",
          "dependencies": [
            "memory/memory.o",
            "parser/parser.o",
            "base/strings.o",
            "base/contexts.o",
            "base/cFunctions.o",
            "base/luaFunctions.o",
            "base/joylolFunctions.o",
            "interpreter/interpreter.o"
          ],
          "outputs": [
            "joylol"
          ]
        }
      }
    }

    def checkExtendedArtefact(baseType, *args) :
      args = list(args)
      lastArg = args.pop()
      for anArg in args :
        t.assertIn(anArg, baseType)
        baseType = baseType[anArg]

    artefacts = am.artefacts
    for taskName in testTasks :
      t.assertIn(taskName, am.tasks)
      chefName = testTasks[taskName]['chefName']
      testTask = testTasks[taskName]['theTask']
      theTask  = am.tasks[taskName]
      for testKey in testTask :
        t.assertIn(testKey, theTask)
        if testKey == 'rule' :
          aRule = testTask['rule']
          t.assertIn(aRule, theTask['rule'])
          t.assertIn('listenForTasks', theTask['rule'][aRule])
        else :
          for testValue in testTask[testKey] :
            t.assertIn(testValue, theTask[testKey])
            t.assertIn('listenForTasks', theTask[testKey][testValue])
      for aDependency in testTask['dependencies'] :
        for anOutput in testTask['outputs'] :
          checkExtendedArtefact(
            artefacts, aDependency, 'creates',   anOutput,    taskName, chefName
          )
          checkExtendedArtefact(
            artefacts, anOutput,    'createdBy', aDependency, taskName, chefName
          )
      if 'secondaryDependencies' not in testTask :
        testTask['secondaryDependencies'] = [ ]
      for aDependency in testTask['secondaryDependencies'] :
        for anOutput in testTask['outputs'] :
          checkExtendedArtefact(
            artefacts, aDependency, 'usedBy', anOutput,    taskName, chefName
          )
          checkExtendedArtefact(
            artefacts, anOutput,    'uses',   aDependency, taskName, chefName
          )

    am.createTupGraphDot('/tmp/artefactsTupGraph.dot')

