import asyncio
import shutil
import unittest
from unittest.mock import patch
import yaml

import json

import inspect

from cputils.natsClient import NatsClient
from cputils.yamlLoader import NoYamlFile, NoYamlDirectory
from cputils.tasksManager import TasksManager
from cputils.settlingTimerMixin import SettlingDict
from cputils.natsListener import ( natsListener, messageCollector,
  hasMessage, getMessages, numMessages )
from tests.testUtils import asyncTestOfProcess

class TestTasksManager(unittest.TestCase):
  """ Test the Tasks Manager. """

  @patch('cputils.yamlLoader.logging')
  def test_loadTasksWithNoDir(t, mock_logging) :
    """Test loading tasks from a directory which does not exist"""

    tm = TasksManager('loadTasksWithNoDir', None)
    with t.assertRaises(NoYamlDirectory) as nrd :
      tm.loadTasksFrom("/this/directory/does/not/exist")
    t.assertEqual(nrd.exception.yamlPath, "/this/directory/does/not/exist")
    mock_logging.error.assert_called_with(
      'No YAML directory found at [/this/directory/does/not/exist]'
    )

  @patch('cputils.yamlLoader.logging')
  def test_loadTasksWithBrokenYaml(t, mock_logging) :
    """Test loading tasks from a broken YAML file"""

    tm = TasksManager('loadTasksithBrokenYaml', None)
    with t.assertRaises(NoYamlFile) as nrf :
      tm.loadTasksFrom("examples/projectsManager/brokenProject")
    t.assertEqual(nrf.exception.yamlPath, "examples/projectsManager/brokenProject/shouldNotLoad.tyml")
    t.assertRegex(nrf.exception.message, r"ScannerError.*mapping values")
    t.assertRegex(
      repr(mock_logging.error.call_args_list),
      r"ScannerError.*mapping values"
    )

  @patch('cputils.yamlLoader.logging')
  def test_loadTasks(t, mock_logging) :
    """ When loading a task set... """

    tm = TasksManager('loadTasks', None)
    tm.loadTasksFrom('examples/projectsManager/joylol')
    t.assertNotEqual(tm, {})
    t.assertIn('tasks', tm.tasksData)

    t.assertIn('cc-cFunctions', tm.tasksData['tasks'])
    t.assertIn('dependencies',  tm.tasksData['tasks']['cc-cFunctions'])
    t.assertIn('base/cFunctions.c', tm.tasksData['tasks']['cc-cFunctions']['dependencies'])
    t.assertIn('outputs',  tm.tasksData['tasks']['cc-cFunctions'])
    t.assertIn('base/cFunctions.o', tm.tasksData['tasks']['cc-cFunctions']['outputs'])
    t.assertIn('rule', tm.tasksData['tasks']['cc-cFunctions'])
    t.assertEqual(tm.tasksData['tasks']['cc-cFunctions']['rule'], 'objectFiles')

    t.assertIn('context', tm.tasksData['tasks'])
    t.assertIn('secondaryDependencies', tm.tasksData['tasks']['context'])
    t.assertIn('memory/memory.jout', tm.tasksData['tasks']['context']['secondaryDependencies'])

  ##########################################################################
  # Registering Artefact Types

  @asyncTestOfProcess(None)
  async def test_registerTasks(t) :
    """ Make sure that any ..."""

    nc = NatsClient("natsTypesListener", 10)
    await nc.connectToServers(["nats://localhost:8888"])

    tasksCollection = SettlingDict(timeOut=0.3)
    await natsListener(
      nc, messageCollector(tasksCollection),
      'register.tasks'
    )

    tm = TasksManager('registerTasks', nc)
    tm.loadTasksFrom('examples/projectsManager/joylol')
    await tm.registerTasks()
    await asyncio.sleep(1)
    await tasksCollection.waitUntilSettled()
    t.assertEqual(len(tasksCollection), 1)
    t.assertTrue('register.tasks' in tasksCollection)
    testTasks = {
      "joylol-memory": {
        "chefName": "registerTasks",
        "taskName": "joylol-memory",
        "theTask": {
          "rule": "joylol",
          "dependencies": [
            "joylol",
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
            "joylol",
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
            "joylol",
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
            "joylol",
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
            "joylol",
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
            "joylol",
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
            "joylol",
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
            "joylol",
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

    msgs = tasksCollection['register.tasks']
    for aTask in msgs :
      t.assertIn('chefName', aTask)
      t.assertEqual(aTask['chefName'], 'registerTasks')
      t.assertIn('taskName', aTask)
      taskName = aTask['taskName']
      t.assertIn(taskName, testTasks)
      testTask = testTasks[taskName]
      t.assertIn('theTask', aTask)
      theTask = aTask['theTask']
      for testKey in testTask['theTask'] :
        t.assertIn(testKey, theTask)
        for testValue in theTask[testKey] :
          t.assertIn(testValue, testTask['theTask'][testKey])
        for testValue in testTask['theTask'][testKey] :
          t.assertIn(testValue, theTask[testKey])
      for testKey in aTask['theTask'] :
        t.assertIn(testKey, testTask['theTask'])
